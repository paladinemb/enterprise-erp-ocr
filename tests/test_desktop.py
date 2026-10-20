import unittest
from unittest.mock import MagicMock, patch

import desktop


class DesktopTests(unittest.TestCase):
    def test_opens_only_the_bound_loopback_service(self):
        service = MagicMock()
        service.server_port = 45678
        service.__enter__.return_value = service
        with patch('desktop.ThreadingHTTPServer', return_value=service) as factory, patch('desktop.webbrowser.open') as browser:
            desktop.main([])
            factory.assert_called_once_with(('127.0.0.1', 0), desktop.Handler)
            browser.assert_called_once_with('http://127.0.0.1:45678/')
            service.serve_forever.assert_called_once()
            service.__exit__.assert_called_once()

    def test_headless_smoke_does_not_open_browser(self):
        with patch('desktop.ThreadingHTTPServer') as factory, patch('desktop.webbrowser.open') as browser:
            desktop.main(['--no-browser'])
            browser.assert_not_called()
            factory.return_value.__enter__.return_value.serve_forever.assert_called_once()
