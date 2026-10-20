import unittest
from unittest.mock import MagicMock, patch

import desktop
from pathlib import Path
import tempfile


class DesktopTests(unittest.TestCase):
    def test_windows_falls_back_to_edge_when_default_browser_is_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            edge = Path(folder)/'Microsoft/Edge/Application/msedge.exe'
            edge.parent.mkdir(parents=True)
            edge.touch()
            with patch('desktop.webbrowser.open', return_value=False), patch('desktop.sys.platform', 'win32'), patch.dict('desktop.os.environ', {'PROGRAMFILES(X86)': folder}), patch('desktop.subprocess.Popen') as launch:
                self.assertTrue(desktop.open_browser('http://127.0.0.1:45678/'))
                launch.assert_called_once_with([str(edge), 'http://127.0.0.1:45678/'])

    def test_browser_error_does_not_stop_service(self):
        with patch('desktop.ThreadingHTTPServer') as factory, patch('desktop.open_browser', side_effect=OSError('no browser')), patch('builtins.print') as output:
            desktop.main([])
            factory.return_value.__enter__.return_value.serve_forever.assert_called_once()
            self.assertIn('no browser', str(output.call_args_list))

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
