"""Document plane correction using existing OpenCV dependency."""
import cv2
import numpy as np


def detect_corners(image):
    height, width = image.shape[:2]
    scale = min(1.0, 1200/max(height, width))
    small = cv2.resize(image, (round(width*scale), round(height*scale)))
    gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (5,5), 0)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    binaries = [mask, cv2.Canny(gray, 50, 150)]
    # Color separates pale paper from a similarly bright desk when gray edges fail.
    lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)
    kernel = np.ones((11,11), np.uint8)
    for channel in (lab[:,:,1], lab[:,:,2]):
        channel = cv2.GaussianBlur(channel,(9,9),0)
        for threshold in np.unique(np.percentile(channel,[20,50,80])):
            binary = np.uint8(channel > threshold)*255
            for region in (binary,255-binary):
                region = cv2.morphologyEx(region,cv2.MORPH_CLOSE,kernel)
                binaries.append(cv2.morphologyEx(region,cv2.MORPH_OPEN,kernel))
    candidates = []
    for binary in binaries:
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            polygon = cv2.approxPolyDP(contour, 0.02*perimeter, True)
            area = cv2.contourArea(polygon)
            points = polygon.reshape(-1,2)
            inside = (points[:,0]>1).all() and (points[:,1]>1).all() and (points[:,0]<small.shape[1]-2).all() and (points[:,1]<small.shape[0]-2).all()
            if len(polygon) == 4 and inside and cv2.isContourConvex(polygon) and 0.35*small.shape[0]*small.shape[1] < area < 0.98*small.shape[0]*small.shape[1]:
                candidates.append((area, points/scale))
    if not candidates:
        return {'detected': False, 'corners': [[0,0],[width-1,0],[width-1,height-1],[0,height-1]]}
    points = max(candidates, key=lambda item:item[0])[1]
    center = points.mean(axis=0)
    points = points[np.argsort(np.arctan2(points[:,1]-center[1], points[:,0]-center[0]))]
    points = np.roll(points, -np.argmin(points.sum(axis=1)), axis=0)
    points[:,0] = np.clip(points[:,0], 0, width-1)
    points[:,1] = np.clip(points[:,1], 0, height-1)
    return {'detected': True, 'corners': points.round(2).tolist()}


def rectify(image, corners):
    try:
        points = np.asarray(corners, dtype=np.float32)
    except (TypeError, ValueError):
        raise ValueError('四角坐标无效。') from None
    height, width = image.shape[:2]
    if points.shape != (4,2) or not np.isfinite(points).all():
        raise ValueError('请按左上、右上、右下、左下设置四个角。')
    if (points < 0).any() or (points[:,0] >= width).any() or (points[:,1] >= height).any():
        raise ValueError('四个角必须位于图片内。')
    if not cv2.isContourConvex(points) or cv2.contourArea(points, oriented=True) <= max(100, width*height*0.01):
        raise ValueError('四角不能交叉或重合，请沿单据边界顺时针设置。')
    top, right, bottom, left = [np.linalg.norm(points[(i+1)%4]-points[i]) for i in range(4)]
    if min(top, right, bottom, left) < 10:
        raise ValueError('选择的单据区域过小。')
    out_width, out_height = round(max(top,bottom))+1, round(max(left,right))+1
    scale = min(1.0, 2200/max(out_width,out_height))
    out_width, out_height = round(out_width*scale), round(out_height*scale)
    target = np.float32([[0,0],[out_width-1,0],[out_width-1,out_height-1],[0,out_height-1]])
    matrix = cv2.getPerspectiveTransform(points, target)
    return cv2.warpPerspective(image, matrix, (out_width,out_height), flags=cv2.INTER_CUBIC, borderValue=(255,255,255))
