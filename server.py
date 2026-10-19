"""Local TableStructureRec service; run with .venv/bin/python server.py."""
import io
import json
import logging
import threading
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAX_BYTES = 15 * 1024 * 1024
LOCK = threading.Lock()
ENGINES = {}


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
    return [row for row in rows if any(row)]


def group_lines(boxes, texts):
    lines = []
    items = sorted(zip(boxes, texts), key=lambda item: min(p[1] for p in item[0]))
    for box, text in items:
        top, bottom = min(p[1] for p in box), max(p[1] for p in box)
        center = (top+bottom)/2
        if not lines or abs(center-lines[-1]['center']) > (bottom-top)*0.6:
            lines.append({'center': center, 'top': top, 'bottom': bottom, 'items': []})
        lines[-1]['items'].append((min(p[0] for p in box), text))
        lines[-1]['bottom'] = max(lines[-1]['bottom'], bottom)
    for line in lines:
        line['text'] = ' '.join(text for x, text in sorted(line['items']))
    return lines


def recognize(image):
    from rapidocr import RapidOCR
    from table_cls import TableCls
    from wired_table_rec.main import WiredTableInput, WiredTableRecognition
    from lineless_table_rec.main import LinelessTableInput, LinelessTableRecognition

    if 'ocr' not in ENGINES:
        ENGINES['ocr'] = RapidOCR()
    if 'classifier' not in ENGINES:
        ENGINES['classifier'] = TableCls()
    output = ENGINES['ocr'](image)
    if output.boxes is None or not output.txts:
        raise ValueError('未识别到文字，请换一张清晰、端正的单据。')
    lines = group_lines(output.boxes, output.txts)
    if len(lines) < 5:
        raise ValueError('需包含四行单据信息及下方物料表格，请检查图片。')
    # shortcut: 沿用前四行作为单据信息的业务规则；其他版式需增加字段定位。
    crop_y = int((lines[3]['bottom']+lines[4]['top'])/2)
    cropped = image[crop_y:]
    ocr_result = []
    for box, text, score in zip(output.boxes, output.txts, output.scores):
        if min(p[1] for p in box) >= crop_y:
            shifted = box.copy()
            shifted[:, 1] -= crop_y
            ocr_result.append([shifted, text, score])
    kind, _ = ENGINES['classifier'](cropped)
    if kind not in ENGINES:
        ENGINES[kind] = (WiredTableRecognition(WiredTableInput()) if kind == 'wired'
                         else LinelessTableRecognition(LinelessTableInput()))
    result = ENGINES[kind](cropped, ocr_result=ocr_result)
    rows = html_rows(result.pred_html or '')
    if not rows:
        raise ValueError('未检测到表格结构，请使用清晰、端正的表格图片。')
    headers = [[line['text']] for line in lines[:4]]
    return {'rows': headers+rows, 'text': '\n'.join('\t'.join(row) for row in headers+rows),
            'engine': 'TableStructureRec', 'table_type': kind}


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
        if self.path not in ('/api/recognize', '/api/corners', '/api/rectify'):
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
        if self.path in ('/api/corners', '/api/rectify'):
            from rectification import detect_corners, rectify
            import cv2
            try:
                if self.path == '/api/corners':
                    return self.reply(200, detect_corners(image))
                corners = json.loads(self.headers.get('X-Document-Corners', 'null'))
                corrected = rectify(image, corners)
                ok, encoded = cv2.imencode('.png', corrected)
                if not ok:
                    raise ValueError('校正图像编码失败，请重试。')
                body = encoded.tobytes()
                self.send_response(200)
                self.send_header('Content-Type', 'image/png')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(body)
                return
            except ValueError as error:
                return self.reply(422, {'error': str(error)})
        if not LOCK.acquire(blocking=False):
            return self.reply(503, {'error': '正在识别另一张图片，请稍后重试。'})
        try:
            self.reply(200, recognize(image))
        except ValueError as error:
            self.reply(422, {'error': str(error)})
        except Exception:
            logging.exception('TableStructureRec inference failed')
            self.reply(500, {'error': '表格识别失败，请检查本地服务终端的模型加载或推理错误。'})
        finally:
            LOCK.release()


if __name__ == '__main__':
    print('OCR: http://127.0.0.1:8765', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8765), Handler).serve_forever()
