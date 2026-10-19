import sys
import unittest
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rectification import detect_corners, rectify


class RectificationTests(unittest.TestCase):
    def setUp(self):
        self.page = np.full((600, 800, 3), 255, np.uint8)
        for x in range(80, 800, 120):
            cv2.line(self.page, (x, 50), (x, 550), (0, 0, 0), 3)
        for y in range(80, 600, 100):
            cv2.line(self.page, (40, y), (760, y), (0, 0, 0), 3)
        self.corners = np.float32([[140, 100], [950, 40], [1030, 800], [60, 710]])
        matrix = cv2.getPerspectiveTransform(np.float32([[0,0],[799,0],[799,599],[0,599]]), self.corners)
        self.photo = cv2.warpPerspective(self.page, matrix, (1100, 900), borderValue=(55,55,55))

    def assert_axes(self, image):
        edges = cv2.Canny(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/1800, 100, minLineLength=200, maxLineGap=15)
        self.assertIsNotNone(lines)
        horizontal, vertical = [], []
        for x1,y1,x2,y2 in lines.reshape(-1,4):
            angle = abs(np.degrees(np.arctan2(y2-y1, x2-x1))) % 180
            if angle < 20 or angle > 160:
                horizontal.append(min(angle, 180-angle))
            if 70 < angle < 110:
                vertical.append(abs(angle-90))
        self.assertGreater(len(horizontal), 3)
        self.assertGreater(len(vertical), 3)
        self.assertLess(np.median(horizontal), 0.5)
        self.assertLess(np.median(vertical), 0.5)

    def test_four_corners_restore_both_axes(self):
        self.assert_axes(rectify(self.photo, self.corners.tolist()))

    def test_automatic_document_boundary_matches_projected_page(self):
        result = detect_corners(self.photo)
        self.assertTrue(result['detected'])
        self.assertLess(np.max(np.linalg.norm(np.array(result['corners'])-self.corners, axis=1)), 8)
        self.assert_axes(rectify(self.photo, result['corners']))

    def test_low_contrast_colored_page_does_not_crop_to_inner_table(self):
        image = np.full((800,1000,3), (205,195,180), np.uint8)
        paper = np.array([[60,55],[950,70],[950,735],[40,720]], np.int32)
        cv2.fillConvexPoly(image, paper, (195,180,182))
        for x in range(110,900,100):
            cv2.line(image, (x,200), (x,650), (55,50,50), 2)
        for y in range(200,651,50):
            cv2.line(image, (110,y), (810,y), (55,50,50), 2)
        result = detect_corners(image)
        self.assertTrue(result['detected'])
        self.assertLess(np.max(np.linalg.norm(np.array(result['corners'])-paper, axis=1)), 20)

    def test_blank_image_has_no_invented_boundary(self):
        result = detect_corners(np.full((300,400,3),255,np.uint8))
        self.assertFalse(result['detected'])
        self.assertEqual(result['corners'], [[0,0],[399,0],[399,299],[0,299]])

    def test_rejects_crossed_repeated_outside_and_nonfinite_corners(self):
        invalid = [ [[0,0],[799,599],[799,0],[0,599]], [[0,0]]*4,
                    [[-1,0],[799,0],[799,599],[0,599]],
                    [[float('nan'),0],[799,0],[799,599],[0,599]], [[0,0],[1,1]] ]
        for corners in invalid:
            with self.subTest(corners=corners), self.assertRaises(ValueError):
                rectify(self.page, corners)

    def test_straight_document_keeps_grid_and_is_not_cropped(self):
        result = rectify(self.page, [[0,0],[799,0],[799,599],[0,599]])
        self.assertEqual(result.shape, self.page.shape)
        np.testing.assert_array_equal(result, self.page)


if __name__ == '__main__':
    unittest.main()
