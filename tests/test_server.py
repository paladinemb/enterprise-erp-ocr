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
from server import Handler, html_rows, group_lines


class TableTests(unittest.TestCase):
    def test_merged_cells_keep_columns_and_text_is_not_executable(self):
        self.assertEqual(html_rows('<table><tr><th rowspan="2">编号</th><th colspan="2">明细</th></tr><tr><td>名称<br>规格</td><td>&lt;script&gt;</td></tr></table>'),
                         [['编号', '明细', ''], ['', '名称\n规格', '<script>']])

    def test_discards_empty_detection_rows(self):
        self.assertEqual(html_rows('<table><tr><td>物料</td></tr><tr><td></td></tr><tr><td>A001</td></tr></table>'), [['物料'], ['A001']])

    def test_ocr_fragments_are_grouped_by_row_before_header_split(self):
        boxes = [[[80,10],[120,10],[120,30],[80,30]], [[0,12],[60,12],[60,32],[0,32]], [[0,70],[60,70],[60,90],[0,90]]]
        self.assertEqual([line['text'] for line in group_lines(boxes, ['PO001','订单编号','日期'])], ['订单编号 PO001','日期'])


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

    def test_serves_only_frontend(self):
        with urllib.request.urlopen(self.url+'/') as response:
            self.assertIn('单据识别', response.read().decode())
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(self.url+'/../server.py')
        self.assertEqual(caught.exception.code, 404)


if __name__ == '__main__':
    unittest.main()
