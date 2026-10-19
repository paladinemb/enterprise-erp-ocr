"""Spatial document sections and regular ruled-table geometry."""
import re
import cv2
import numpy as np

LABEL = re.compile(r'编号|编码|名称|规格|型号|单位|数量|单价|金额|备注|序号|品名|税率|项目|description|quantity|qty|price|amount|item|code|name|unit', re.I)
FOOTER = re.compile(r'^(合计|总计|小计|制单|核批|审核|审批|承办|签字|签名|备注[：:]|total\b|subtotal\b)', re.I)


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


def split_sections(boxes, texts, bounds):
    _, top, _, bottom = bounds
    header, footer = [], []
    for line in group_lines(boxes, texts):
        if line['center'] < top:
            header.append(line['text'])
        elif line['center'] > bottom:
            footer.append(line['text'])
    return header, footer


def header_row_count(rows):
    count = 0
    for row in rows:
        if sum(bool(LABEL.search(cell)) for cell in row) < 2:
            break
        count += 1
    return count


def _positions(profile, threshold):
    hits = np.flatnonzero(profile > threshold)
    groups = np.split(hits, np.flatnonzero(np.diff(hits) > 3)+1)
    return [int(round(group.mean())) for group in groups if len(group)]


def find_grid(image):
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((1,max(25,width//20)), np.uint8))
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((max(25,height//20),1), np.uint8))
    mask = cv2.dilate(horizontal | vertical, np.ones((3,3), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in sorted(contours, key=cv2.contourArea, reverse=True):
        x,y,w,h = cv2.boundingRect(contour)
        if w*h < width*height*.08:
            continue
        xs = [x+p for p in _positions(np.count_nonzero(vertical[y:y+h,x:x+w], axis=0), h*.65)]
        ys = [y+p for p in _positions(np.count_nonzero(horizontal[y:y+h,x:x+w], axis=1), w*.65)]
        if len(xs) >= 3 and len(ys) >= 3:
            # Only use a rectangular grid when every row/column boundary spans it.
            if abs(xs[0]-x)>8 or abs(xs[-1]-(x+w))>8 or abs(ys[0]-y)>8 or abs(ys[-1]-(y+h))>8:
                continue
            return {'xs': xs, 'ys': ys, 'bounds': (xs[0],ys[0],xs[-1],ys[-1])}
    return None


def text_crop(image):
    """Skip empty cells; trim to actual ink so single digits remain readable."""
    if not image.size:
        return None
    gray = cv2.GaussianBlur(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), (3,3), 0)
    ink = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,15)
    _, _, stats, _ = cv2.connectedComponentsWithStats(ink)
    height, width = gray.shape
    parts = [s for s in stats[1:] if s[cv2.CC_STAT_AREA]>=max(5,height*width*.002) and s[cv2.CC_STAT_HEIGHT]>=max(4,height*.18)]
    if not parts:
        return None
    left,top = min(s[0] for s in parts), min(s[1] for s in parts)
    right,bottom = max(s[0]+s[2] for s in parts), max(s[1]+s[3] for s in parts)
    cropped = image[max(0,top-3):min(height,bottom+3), max(0,left-3):min(width,right+3)]
    return cv2.copyMakeBorder(cropped,6,6,6,6,cv2.BORDER_REPLICATE)


def read_grid(image, grid, ocr):
    xs, ys = grid['xs'], grid['ys']
    # shortcut: empty narrow strips between double rules are treated as border spacing.
    # Preserve narrow columns containing text; use structure models for merged grids.
    mask = np.zeros(image.shape[:2],np.uint8)
    for x in xs:
        cv2.line(mask,(x,ys[0]),(x,ys[-1]),255,9)
    for y in ys:
        cv2.line(mask,(xs[0],y),(xs[-1],y),255,9)
    clean = cv2.inpaint(image,mask,3,cv2.INPAINT_TELEA)
    gaps = np.diff(xs)
    remove = set()
    for i,gap in enumerate(gaps):
        if 0 < i < len(gaps)-1 and gap < np.median(gaps)*.45:
            if all(text_crop(clean[a+5:b-5,xs[i]+5:xs[i+1]-5]) is None for a,b in zip(ys,ys[1:])):
                remove.add(i)
    xs = [x for i,x in enumerate(xs) if i not in remove]
    rows, warnings = [], []
    for r,(top,bottom) in enumerate(zip(ys,ys[1:])):
        row = []
        for c,(left,right) in enumerate(zip(xs,xs[1:])):
            cell = text_crop(clean[top+5:bottom-5,left+5:right-5])
            text = ''
            if cell is not None:
                output = ocr(cell, use_det=False, use_cls=False)
                if output.txts and output.scores[0] >= .65:
                    text = output.txts[0].strip()
                    if output.scores[0] < .9:
                        warnings.append(f'第 {r+1} 行第 {c+1} 列文字置信度较低，请核对。')
                else:
                    warnings.append(f'第 {r+1} 行第 {c+1} 列有痕迹但未可靠识别，请核对原图。')
            row.append(text)
        rows.append(row)
    return rows, warnings


def lineless_bounds(boxes, texts, shape):
    lines = group_lines(boxes, texts)
    start = next((i for i,line in enumerate(lines) if sum(bool(LABEL.search(text)) for _,text in line['items']) >= 2), None)
    if start is None:
        raise ValueError('未可靠定位表格列名，无法区分表头与表体，请换一张清晰图片。')
    end = next((i for i in range(start+1,len(lines)) if FOOTER.search(lines[i]['text'])), len(lines))
    if end <= start+1:
        raise ValueError('表格列名下方未检测到表体。')
    top = max(0, int(lines[start]['top'])-8)
    bottom = min(shape[0], int(lines[end-1]['bottom'])+8)
    return (0,top,shape[1],bottom)
