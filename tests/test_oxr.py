import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server

class OXRTests(unittest.TestCase):
    def test_oxr_table_keeps_headers_footer_and_empty_cells(self):
        output = ['采购订单\n订单编号 001\n编号 名称\n001 螺栓\n合计 10', '<table><tr><td colspan="2">采购订单</td></tr><tr><th>编号</th><th>名称</th></tr><tr><td>001</td><td></td></tr></table>']
        with patch('oxr_backend.read', side_effect=output):
            data = server.recognize(np.full((300,400,3),255,np.uint8))
        self.assertEqual(data['rows'], [['编号','名称'],['001','']])
        self.assertEqual(data['header'], ['采购订单','订单编号 001'])
        self.assertEqual(data['footer'], ['合计 10'])
        self.assertEqual(data['engine'], 'SoMark OXR-1.0 / MLX')

    def test_invalid_or_multiple_tables_fail_without_silently_losing_data(self):
        from oxr_backend import table_rows
        for text in ['no table', '<table><tr><td>x</td></tr>', '<table><tr><td>a</td></tr></table><table><tr><td>b</td></tr></table>']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                table_rows(text)

    def test_no_legacy_ocr_models_are_imported(self):
        source = Path(server.__file__).read_text()
        self.assertNotIn('from rapidocr',source)
        self.assertNotIn('from table_cls',source)

    def test_upright_example_alignment_needs_no_model(self):
        import cv2
        image=cv2.imread(str(Path(__file__).parent/"fixtures/example-purchase-order.png"))
        corrected,info=server.align(image)
        self.assertFalse(info["changed"])

    def test_blank_alignment_is_rejected(self):
        with self.assertRaises(ValueError):
            server.align(np.full((200,300,3),255,np.uint8))

if __name__ == '__main__': unittest.main()
