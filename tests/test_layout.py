import sys
import unittest
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from document_layout import find_grid, split_sections, header_row_count, read_grid, text_crop, lineless_bounds


class LayoutTests(unittest.TestCase):
    def test_grid_preserves_eight_empty_body_rows(self):
        image = np.full((600, 900, 3), 245, np.uint8)
        for x in [40, 120, 340, 500, 600, 700, 850]:
            cv2.line(image, (x, 130), (x, 490), (0, 0, 0), 2)
        for y in range(130, 491, 40):
            cv2.line(image, (40, y), (850, y), (0, 0, 0), 2)
        grid = find_grid(image)
        self.assertIsNotNone(grid)
        self.assertEqual(len(grid['xs'])-1, 6)
        self.assertEqual(len(grid['ys'])-1, 9)

    def test_tilted_internal_grid_is_read_without_paper_corners(self):
        image = np.full((600,900,3),245,np.uint8)
        for x in [40,120,340,500,600,700,850]:
            cv2.line(image,(x,130),(x,490),(0,0,0),2)
        for y in range(130,491,40):
            cv2.line(image,(40,y),(850,y),(0,0,0),2)
        rotated=cv2.warpAffine(image,cv2.getRotationMatrix2D((450,300),3,1),(900,600),borderValue=(245,245,245))
        grid=find_grid(rotated)
        self.assertIsNotNone(grid)
        self.assertEqual(len(grid['xs'])-1,6)
        self.assertEqual(len(grid['ys'])-1,9)

    def test_perspective_invoice_with_broken_edges_and_outside_marks(self):
        image = np.full((500,1000,3),230,np.uint8)
        source = np.float32([[100,180],[940,180],[940,480],[100,480]])
        target = np.float32([[115,187],[940,194],[974,482],[87,485]])
        matrix = cv2.getPerspectiveTransform(source,target)
        def line(a,b):
            points=cv2.perspectiveTransform(np.float32([[a,b]]),matrix)[0].astype(int)
            cv2.line(image,tuple(points[0]),tuple(points[1]),(30,30,30),1)
        for x in [100,145,355,490,535,625,715,815,940]:
            line((x,180),(x,480))
        for y in range(180,481,30):
            line((100,y),(940,y))
        cv2.line(image,(70,7),(999,18),(30,30,30),2)
        cv2.line(image,(650,493),(999,493),(30,30,30),2)
        cv2.putText(image,'8',(20,470),cv2.FONT_HERSHEY_SIMPLEX,1,(30,30,30),2)
        grid=find_grid(image)
        self.assertIsNotNone(grid)
        self.assertEqual(len(grid['xs'])-1,8)
        self.assertEqual(len(grid['ys'])-1,10)

    def test_sections_follow_geometry_with_one_or_seven_heading_lines(self):
        for count in (1, 7):
            boxes = [[[10,y],[120,y],[120,y+10],[10,y+10]] for y in range(5, count*15, 15)]
            texts = [f'抬头{i}' for i in range(count)]
            top = count*15+10
            boxes += [[[0,top+20],[80,top+20],[80,top+30],[0,top+30]],
                      [[10,top+100],[120,top+100],[120,top+110],[10,top+110]]]
            texts += ['物资名称', '制单 核批 承办']
            header, footer = split_sections(boxes, texts, (0,top,200,top+80))
            self.assertEqual(header, texts[:count])
            self.assertEqual(footer, ['制单 核批 承办'])

    def test_header_rows_depend_on_column_labels_not_a_fixed_line_count(self):
        self.assertEqual(header_row_count([['编号','物资名称','规格型号','单位','数量','备注'], ['1','','','','','']]), 1)
        self.assertEqual(header_row_count([['A001','轴承','20'], ['A002','螺栓','100']]), 0)
        self.assertEqual(header_row_count([['物料名称','金额'],['规格型号','单价'],['轴承','35']]), 2)

    def test_title_keywords_do_not_become_a_wireless_table_header(self):
        boxes = [[[10,10],[300,10],[300,30],[10,30]],
                 [[10,100],[100,100],[100,120],[10,120]],
                 [[200,100],[280,100],[280,120],[200,120]],
                 [[10,150],[100,150],[100,170],[10,170]],
                 [[200,150],[280,150],[280,170],[200,170]],
                 [[10,220],[200,220],[200,240],[10,240]]]
        bounds = lineless_bounds(boxes,['物资名称与数量统计表','物资名称','数量','轴承','20','合计 20'],(300,400,3))
        self.assertEqual(bounds,(0,92,400,178))

    def test_empty_cells_do_not_invent_text_or_drop_rows(self):
        image = np.full((220,400,3),245,np.uint8)
        xs,ys = [20,140,260,380],[20,80,140,200]
        for x in xs:
            cv2.line(image,(x,20),(x,200),(0,0,0),2)
        for y in ys:
            cv2.line(image,(20,y),(380,y),(0,0,0),2)
        def no_text(*args,**kwargs):
            self.fail('OCR must not run on a blank cell')
        rows,warnings = read_grid(image,{'xs':xs,'ys':ys},no_text)
        self.assertEqual(rows,[['','','']]*3)
        self.assertFalse(warnings)

    def test_text_crop_distinguishes_blank_from_single_digit_ink(self):
        blank = np.full((50,80,3),200,np.uint8)
        self.assertIsNone(text_crop(blank))
        cv2.putText(blank,'1',(30,35),cv2.FONT_HERSHEY_SIMPLEX,.8,(20,20,20),2)
        self.assertIsNotNone(text_crop(blank))


if __name__ == '__main__':
    unittest.main()
