"""Run with Windows x64 Python 3.12 after installing the locked requirements."""
import os
from pathlib import Path
import subprocess
import sys


def main():
    if sys.platform != 'win32':
        raise SystemExit('Build the Windows executable on Windows, or use GitHub Actions.')
    os.chdir(Path(__file__).resolve().parents[1])
    from rapidocr import RapidOCR
    from table_cls import TableCls
    from wired_table_rec.main import WiredTableInput, WiredTableRecognition
    from lineless_table_rec.main import LinelessTableInput, LinelessTableRecognition

    # Download the default models before collecting package data for offline use.
    RapidOCR(params={'Global.max_side_len': 1280})
    TableCls()
    WiredTableRecognition(WiredTableInput())
    LinelessTableRecognition(LinelessTableInput())
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
               '--onefile', '--console', '--name', 'ERP-OCR',
               '--distpath', 'release', '--workpath', 'build/windows',
               '--specpath', 'build', '--paths', '.',
               '--add-data', 'dist:dist', '--add-data', 'third_party:third_party']
    for package in ('rapidocr', 'table_cls', 'wired_table_rec', 'lineless_table_rec', 'onnxruntime'):
        command += ['--collect-all', package]
    subprocess.run(command + ['desktop.py'], check=True)


if __name__ == '__main__':
    main()
