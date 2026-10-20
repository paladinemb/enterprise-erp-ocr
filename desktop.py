"""Desktop entry point; the existing server remains usable for development."""
import argparse
import webbrowser
from http.server import ThreadingHTTPServer

from server import Handler


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args(argv)
    with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as service:
        url = f'http://127.0.0.1:{service.server_port}/'
        print(url, flush=True)
        print('Keep this window open. Close it to stop ERP OCR.', flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        try:
            service.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
