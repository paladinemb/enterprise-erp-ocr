import sys
import unittest
from pathlib import Path
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rectification import align_text

class TextAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.image = np.full((300,500,3),255,np.uint8)
        self.boxes = np.float32([[[40,y],[400,y],[400,y+30],[40,y+30]] for y in (40,110,180)])
        for box in self.boxes:
            cv2.polylines(self.image,[box.astype(np.int32)],True,(0,0,0),2)

    def test_straight_text_without_paper_edges_is_unchanged(self):
        corrected,info=align_text(self.image,self.boxes)
        self.assertFalse(info['changed'])
        np.testing.assert_array_equal(corrected,self.image)

    def test_rotated_and_sheared_text_is_aligned_without_cropping(self):
        for angle,shear in [(7,0),(-8,0),(0,.12)]:
            radians=np.radians(angle)
            basis=np.array([[np.cos(radians),-np.sin(radians)+shear],[np.sin(radians),np.cos(radians)]])
            boxes=self.boxes@basis.T+np.array([50,50])
            image=np.full((450,650,3),255,np.uint8)
            corrected,info=align_text(image,boxes)
            self.assertTrue(info['changed'])
            matrix=np.array(info['matrix'])
            out=cv2.transform(boxes.astype(np.float32),matrix)
            self.assertLess(np.max(abs(out[:,1,1]-out[:,0,1])),1)
            self.assertLess(np.max(abs(out[:,3,0]-out[:,0,0])),1)
            frame=cv2.transform(np.float32([[[0,0],[649,0],[649,449],[0,449]]]),matrix)[0]
            self.assertTrue((frame>=-.01).all())
            self.assertLessEqual(frame[:,0].max(),corrected.shape[1])
            self.assertLessEqual(frame[:,1].max(),corrected.shape[0])

    def test_no_text_reports_a_text_error(self):
        with self.assertRaisesRegex(ValueError,'文字'):
            align_text(self.image,None)

    def test_conflicting_text_directions_are_not_silently_distorted(self):
        boxes=self.boxes.copy()
        boxes[0,:,1]+=boxes[0,:,0]*.2
        boxes[1,:,1]-=boxes[1,:,0]*.2
        with self.assertRaisesRegex(ValueError,'方向'):
            align_text(self.image,boxes)

if __name__=='__main__': unittest.main()
