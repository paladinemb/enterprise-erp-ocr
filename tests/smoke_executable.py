"""Exercise the packaged HTTP server and real OCR without opening a browser."""
import json
from pathlib import Path
import queue
import subprocess
import sys
import threading
from urllib.request import Request, urlopen


def main(command):
    process = subprocess.Popen(command + ['--no-browser'], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    lines = queue.Queue()
    def read_output():
        for line in process.stdout:
            print(line.rstrip(), flush=True)
            if line.startswith('http://127.0.0.1:'):
                lines.put(line.strip())
        lines.put(None)
    threading.Thread(target=read_output, daemon=True).start()
    try:
        url = lines.get(timeout=180)
        assert url, 'Executable stopped before starting its local server'
        with urlopen(url, timeout=30) as response:
            assert '单据识别' in response.read().decode('utf-8')
        for resource in ('app.js', 'core.js', 'vendor/xlsx.full.min.js'):
            with urlopen(url + resource, timeout=30) as response:
                assert response.status == 200
                assert response.read()
        fixture = Path(__file__).parent/'fixtures/example-purchase-order.png'
        headers = {'Content-Type': 'image/png', 'Origin': url.rstrip('/')}
        with urlopen(Request(url+'api/align', data=fixture.read_bytes(), headers=headers), timeout=180) as response:
            image = response.read()
            assert response.headers['Content-Type'] == 'image/png'
        with urlopen(Request(url+'api/recognize', data=image, headers=headers), timeout=180) as response:
            result = json.load(response)
        text = result['text']
        assert all(value in text for value in ('A001', 'A002', 'A003', '700.00', '250.00', '300.00')), result
        assert len(result['rows']) == 4, result
        assert all(len(row) == 5 for row in result['rows']), result
        print('PASS: packaged assets, alignment and real OCR (3 items, 5 columns)')
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == '__main__':
    main(sys.argv[1:])
