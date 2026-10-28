"""Align detected text directions without detecting or cropping paper edges."""
import cv2
import numpy as np


def align_text(image, boxes):
    if boxes is None:
        raise ValueError('未检测到清晰文字，无法判断文字方向，请换一张清晰图片。')
    horizontal, vertical = [], []
    for box in np.asarray(boxes,dtype=np.float32).reshape(-1,4,2):
        top = ((box[1]-box[0])+(box[2]-box[3]))/2
        side = ((box[3]-box[0])+(box[2]-box[1]))/2
        if np.linalg.norm(top) < 1.5*np.linalg.norm(side):
            continue
        horizontal.append(np.degrees(np.arctan2(top[1],top[0])))
        vertical.append(np.degrees(np.arctan2(side[0],side[1])))
    if not horizontal:
        raise ValueError('文字方向未能可靠判断，请上传包含清晰文字行的图片。')
    h,v = float(np.median(horizontal)),float(np.median(vertical))
    if np.percentile(horizontal,90)-np.percentile(horizontal,10)>5 or abs(h)>20 or abs(v)>20 or np.median(np.abs(np.array(horizontal)-h))>3 or np.median(np.abs(np.array(vertical)-v))>3:
        raise ValueError('文字方向差异较大，无法可靠自动拉正，请重新拍摄。')
    changed = max(abs(h),abs(v)) >= .35
    height,width = image.shape[:2]
    if not changed and max(height,width)<=2200:
        return image, {'changed':False,'angle':h,'matrix':[[1,0,0],[0,1,0]]}
    if not changed:
        h=v=0
    h,v = np.radians([h,v])
    basis=np.array([[np.cos(h),np.sin(v)],[np.sin(h),np.cos(v)]])
    transform=np.linalg.inv(basis)
    frame=np.float32([[0,0],[width-1,0],[width-1,height-1],[0,height-1]])@transform.T
    minimum=np.floor(frame.min(axis=0))
    size=np.ceil(frame.max(axis=0))-minimum+1
    matrix=np.column_stack((transform,-minimum))
    scale=min(1.,2200/max(size))
    matrix*=scale
    out_width,out_height=np.ceil(size*scale).astype(int)
    corrected=cv2.warpAffine(image,matrix,(out_width,out_height),flags=cv2.INTER_CUBIC,borderValue=(255,255,255))
    return corrected, {'changed':changed,'angle':float(np.degrees(h)),'matrix':matrix.tolist()}


def text_boxes(image):
    """Estimate text-line angles using image morphology, without legacy OCR weights."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    ink = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,15)
    height,width = gray.shape
    for kernel in (np.ones((1,max(40,width//12)),np.uint8), np.ones((max(40,height//12),1),np.uint8)):
        ink = cv2.subtract(ink,cv2.morphologyEx(ink,cv2.MORPH_OPEN,kernel))
    joined = cv2.dilate(ink,np.ones((3,max(9,width//80)),np.uint8))
    contours,_ = cv2.findContours(joined,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    boxes=[]
    for contour in contours:
        (x,y),(w,h),angle = cv2.minAreaRect(contour)
        if w < h:
            w,h,angle=h,w,angle+90 if angle < 0 else angle-90
        if w < max(25,width*.03) or h < 5 or w < 2*h or h > height*.15:
            continue
        a=np.radians(angle)
        along=np.array([np.cos(a),np.sin(a)])*w/2
        down=np.array([-np.sin(a),np.cos(a)])*h/2
        center=np.array([x,y])
        boxes.append([center-along-down,center+along-down,center+along+down,center-along+down])
    return np.array(boxes) if boxes else None
