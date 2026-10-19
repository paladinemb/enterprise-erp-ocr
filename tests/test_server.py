import io
import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Handler, html_rows, group_lines, read_footer


class TableTests(unittest.TestCase):
    def test_merged_cells_keep_columns_and_text_is_not_executable(self):
        self.assertEqual(html_rows('<table><tr><th rowspan="2">编号</th><th colspan="2">明细</th></tr><tr><td>名称<br>规格</td><td>&lt;script&gt;</td></tr></table>'),
                         [['编号', '明细', ''], ['', '名称\n规格', '<script>']])

    def test_preserves_empty_table_rows(self):
        self.assertEqual(html_rows('<table><tr><td>物料</td></tr><tr><td></td></tr><tr><td>A001</td></tr></table>'), [['物料'], [''], ['A001']])

    def test_ocr_fragments_are_grouped_by_row_before_header_split(self):
        boxes = [[[80,10],[120,10],[120,30],[80,30]], [[0,12],[60,12],[60,32],[0,32]], [[0,70],[60,70],[60,90],[0,90]]]
        self.assertEqual([line['text'] for line in group_lines(boxes, ['PO001','订单编号','日期'])], ['订单编号 PO001','日期'])

    def test_red_date_overlay_does_not_mix_with_printed_footer(self):
        import numpy as np
        from types import SimpleNamespace
        image = np.full((100,300,3),200,np.uint8)
        image[70:85,200:280] = (0,0,240)
        results = iter([
            SimpleNamespace(txts=['2012 11 19']),
            SimpleNamespace(boxes=[[[20,10],[100,10],[100,40],[20,40]],
                                   [[400,10],[550,10],[550,40],[400,40]]],txts=['制单','602'])
        ])
        footer,warnings = read_footer(image,50,['混合文字'],lambda *args:next(results))
        self.assertEqual(footer,['制单','红色日期标记：2012 11 19'])
        self.assertTrue(warnings)


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request_error(self, data, headers, expected):
        req = urllib.request.Request(self.url+'/api/recognize', data=data, headers=headers)
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(req)
        self.assertEqual(caught.exception.code, expected)
        self.assertIn('error', json.load(caught.exception))

    def test_rejects_cross_site_image(self):
        self.request_error(b'bad', {'Content-Type':'image/png','Origin':'https://example.org'}, 403)

    def test_rejects_invalid_image_before_loading_models(self):
        self.request_error(b'bad', {'Content-Type':'image/png'}, 400)

    def test_rejects_non_image(self):
        self.request_error(b'bad', {'Content-Type':'text/plain'}, 415)

    def test_text_alignment_returns_png_and_straight_metadata(self):
        from unittest.mock import patch
        image = (Path(__file__).parent/'fixtures/example-purchase-order.png').read_bytes()
        request = urllib.request.Request(self.url+'/api/align',data=image,headers={'Content-Type':'image/png'})
        with patch('server.align',side_effect=lambda picture:(picture,{'changed':False,'angle':0})):
            with urllib.request.urlopen(request) as response:
                self.assertEqual(response.headers['Content-Type'],'image/png')
                self.assertFalse(json.loads(response.headers['X-Alignment'])['changed'])
                self.assertTrue(response.read().startswith(b'\x89PNG'))

    def test_phone_exif_orientation_is_applied_before_text_analysis(self):
        from PIL import Image
        from unittest.mock import patch
        picture = Image.new('RGB',(80,40),'white')
        exif=picture.getexif();exif[274]=6
        stream=io.BytesIO();picture.save(stream,format='JPEG',exif=exif)
        request=urllib.request.Request(self.url+'/api/align',data=stream.getvalue(),headers={'Content-Type':'image/jpeg'})
        with patch('server.align',side_effect=lambda picture:(picture,{'changed':False,'angle':0})) as alignment:
            with urllib.request.urlopen(request) as response:
                self.assertEqual(response.status,200)
            self.assertEqual(alignment.call_args.args[0].shape[:2],(80,40))

    def test_unreliable_text_direction_returns_error(self):
        from unittest.mock import patch
        image = (Path(__file__).parent/'fixtures/example-purchase-order.png').read_bytes()
        request=urllib.request.Request(self.url+'/api/align',data=image,headers={'Content-Type':'image/png'})
        with patch('server.align',side_effect=ValueError('文字方向无法可靠判断')):
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request)
            self.assertEqual(caught.exception.code,422)
            self.assertIn('文字方向',json.load(caught.exception)['error'])

    def test_serves_only_frontend(self):
        with urllib.request.urlopen(self.url+'/') as response:
            self.assertIn('单据识别', response.read().decode())
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(self.url+'/../server.py')
        self.assertEqual(caught.exception.code, 404)


if __name__ == '__main__':
    unittest.main()
