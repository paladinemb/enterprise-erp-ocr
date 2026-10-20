"""Desktop entry point; the existing server remains usable for development."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import webbrowser
from http.server import ThreadingHTTPServer

from server import Handler


def open_browser(url):
    try:
        if webbrowser.open(url):
            return True
    except (OSError, webbrowser.Error) as error:
        print(f'Default browser failed: {error}', flush=True)
    if sys.platform == 'win32':
        for variable in ('PROGRAMFILES(X86)', 'PROGRAMFILES', 'LOCALAPPDATA'):
            folder = os.environ.get(variable)
            if folder:
                edge = Path(folder)/'Microsoft/Edge/Application/msedge.exe'
                if edge.is_file():
                    subprocess.Popen([str(edge), url])
                    print('Opened Microsoft Edge as a fallback.', flush=True)
                    return True
    return False


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args(argv)
    with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as service:
        url = f'http://127.0.0.1:{service.server_port}/'
        print(url, flush=True)
        print('Keep this window open. Close it to stop ERP OCR.', flush=True)
        print('If no page opens, copy the URL above into your browser.', flush=True)
        if not args.no_browser:
            try:
                if not open_browser(url):
                    print('Browser did not open automatically. Open the URL above manually.', flush=True)
            except OSError as error:
                print(f'Browser launch failed: {error}. Open the URL above manually.', flush=True)
        try:
            service.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
