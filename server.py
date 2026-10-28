"""Local SoMark OXR service; run with .venv/bin/python server.py."""
import io
import json
import logging
import threading
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from document_layout import group_lines, find_grid, split_sections, read_grid, header_row_count, lineless_bounds

ROOT = Path(__file__).resolve().parent
MAX_BYTES = 15 * 1024 * 1024
LOCK = threading.Lock()


def html_rows(html):
    class TableParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.cells = {}
            self.row = -1
            self.col = 0
            self.current = None

        def handle_starttag(self, tag, attrs):
            if tag == 'tr':
                self.row += 1
                self.col = 0
            elif tag in ('td', 'th'):
                while (self.row, self.col) in self.cells:
                    self.col += 1
                attrs = dict(attrs)
                self.current = (self.row, self.col)
                for r in range(max(1, min(2000, int(attrs.get('rowspan', 1))))):
                    for c in range(max(1, min(200, int(attrs.get('colspan', 1))))):
                        self.cells[self.row+r, self.col+c] = ''
            elif tag == 'br' and self.current is not None:
                self.cells[self.current] += '\n'

        def handle_data(self, data):
            if self.current is not None:
                self.cells[self.current] += data

        def handle_endtag(self, tag):
            if tag in ('td', 'th'):
                self.current = None
                self.col += 1

    parser = TableParser()
    parser.feed(html)
    if not parser.cells:
        return []
    height = max(r for r, c in parser.cells)+1
    width = max(c for r, c in parser.cells)+1
    rows = [[parser.cells.get((r, c), '').strip() for c in range(width)] for r in range(height)]
    return rows


def align(image):
    from rectification import align_text, text_boxes
    return align_text(image, text_boxes(image))


def recognize(image):
    from oxr_backend import read, table_rows
    from document_layout import LABEL, FOOTER
    full_text = read(image)
    rows = table_rows(read(image, 'table'))
    lines = [line.strip() for line in full_text.splitlines() if line.strip()]
    # shortcut: without the official layout model, unruled sections use field labels; review unusual layouts.
    start = next((i for i,line in enumerate(lines) if len(LABEL.findall(line)) >= 2), None)
    end = next((i for i,line in enumerate(lines) if i > (start if start is not None else -1)
                and FOOTER.search(line)), len(lines))
    header = lines[:start] if start is not None else []
    footer = lines[end:]
    normalize = lambda text: ''.join(text.split())
    sections = {normalize(line) for line in header+footer}
    while rows and len([cell for cell in rows[0] if cell]) == 1 and normalize(''.join(rows[0])) in sections:
        rows.pop(0)
    while rows and len([cell for cell in rows[-1] if cell]) == 1 and normalize(''.join(rows[-1])) in sections:
        rows.pop()
    if not rows:
        raise ValueError('未识别到表格明细，请核对原图。')
    warnings = ['OXR 生成结果需核对编号、数量和金额；未提供逐字置信度。',
                '本机版本未接入官方布局模型，抬头和表尾按字段分段，请与原图核对。']
    if start is None:
        warnings.append('未可靠区分抬头与表体，完整识别文字已保留在下方文本区。')
    return {'header': header, 'rows': rows, 'footer': footer,
            'header_rows': header_row_count(rows), 'warnings': warnings,
            'text': full_text, 'engine': 'SoMark OXR-1.0 / MLX', 'table_type': 'oxr'}


def read_footer(image, bottom, fallback, ocr):
    """Separate a red date overlay from overlapping dark footer print."""
    import cv2
    import numpy as np
    import re
    crop = image[int(bottom)+3:]
    if not crop.size:
        return fallback, []
    red = crop[:,:,2].astype(int)-np.maximum(crop[:,:,0],crop[:,:,1]).astype(int) > 45
    if np.count_nonzero(red) < 30:
        return fallback, []
    isolated = np.full_like(crop,255)
    isolated[red] = 0
    date = ocr(cv2.resize(isolated,None,fx=2,fy=2))
    date_text = ' '.join(date.txts or [])
    if not re.fullmatch(r'\d{4}\s*\d{1,2}\s*\d{1,2}',date_text):
        return fallback, []
    dark = cv2.adaptiveThreshold(crop[:,:,2],255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,31,15)
    printed = ocr(cv2.cvtColor(cv2.resize(dark,None,fx=2,fy=2),cv2.COLOR_GRAY2BGR))
    red_x = np.flatnonzero(red.any(axis=0))
    clear_boxes, clear_texts = [], []
    if printed.boxes is not None:
        for box,text in zip(printed.boxes,printed.txts):
            center_x = sum(p[0] for p in box)/8
            if not red_x[0]-15 <= center_x <= red_x[-1]+15:
                clear_boxes.append(box)
                clear_texts.append(text)
    lines = [line['text'] for line in group_lines(clear_boxes,clear_texts)]
    return lines+['红色日期标记：'+date_text], ['表尾日期栏与红色标记重叠，印刷文字未完全识别；红色日期单独列出，请核对原图。']


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT/'dist'), **kwargs)

    def reply(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path not in ('/api/recognize', '/api/align'):
            return self.reply(404, {'error': '接口不存在。'})
        allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        host = self.headers.get('Host', '')
        if host not in allowed or self.headers.get('Origin', 'http://'+host) != 'http://'+host:
            return self.reply(403, {'error': '仅允许本机页面调用。'})
        if self.headers.get('Content-Type') not in ('image/png', 'image/jpeg', 'image/webp'):
            return self.reply(415, {'error': '请选择 JPG、PNG 或 WebP 图片。'})
        try:
            size = int(self.headers.get('Content-Length', 0))
        except ValueError:
            size = 0
        if not 0 < size <= MAX_BYTES:
            return self.reply(413, {'error': '图片为空或超过 15 MB。'})
        data = self.rfile.read(size)
        from PIL import Image, ImageOps
        import numpy as np
        try:
            with Image.open(io.BytesIO(data)) as picture:
                if picture.format not in ('PNG', 'JPEG', 'WEBP'):
                    raise ValueError('图片格式不支持。')
                if picture.width*picture.height > 25000000:
                    raise ValueError('图片尺寸超过 2500 万像素。')
                image = np.array(ImageOps.exif_transpose(picture).convert('RGB'))[:, :, ::-1].copy()
        except (ValueError, OSError, Image.DecompressionBombError) as error:
            return self.reply(400, {'error': '无法读取图片，或图片尺寸超限。'})
        if not LOCK.acquire(blocking=False):
            return self.reply(503, {'error': '正在识别另一张图片，请稍后重试。'})
        try:
            if self.path == '/api/align':
                import cv2
                corrected, info = align(image)
                ok, encoded = cv2.imencode('.png', corrected)
                if not ok:
                    raise ValueError('文字方向校正图像编码失败，请重试。')
                body = encoded.tobytes()
                self.send_response(200)
                self.send_header('Content-Type','image/png')
                self.send_header('Content-Length',str(len(body)))
                self.send_header('X-Alignment',json.dumps({'changed':info['changed'],'angle':info['angle']}))
                self.send_header('Cache-Control','no-store')
                self.end_headers()
                self.wfile.write(body)
            else:
                self.reply(200, recognize(image))
        except ValueError as error:
            self.reply(422, {'error': str(error)})
        except Exception:
            logging.exception('OXR inference failed')
            self.reply(500, {'error': '表格识别失败，请检查本地服务终端的模型加载或推理错误。'})
        finally:
            LOCK.release()


if __name__ == '__main__':
    print('OCR: http://127.0.0.1:8765', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8765), Handler).serve_forever()
