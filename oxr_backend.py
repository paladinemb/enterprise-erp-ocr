"""Local SoMark OXR inference on Apple Silicon; no remote OCR calls."""
import os
import platform
import re
from pathlib import Path

MODEL_REVISION = 'c708407f9d2b4df658f2543d9132b62bb7221df4'
MODEL_PATH = Path(os.environ.get('OXR_MODEL_PATH', Path(__file__).parent/'models/OXR-1.0'))
_ENGINE = None


def read(image, task='text'):
    global _ENGINE
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise ValueError('此版本需要 Apple Silicon Mac 和 MLX。')
    if not (MODEL_PATH/'model.safetensors').is_file():
        raise ValueError('未找到 OXR 权重，请按 README 下载模型或设置 OXR_MODEL_PATH。')
    from mlx_vlm import load, generate
    from mlx_vlm.prompt_utils import apply_chat_template
    from PIL import Image
    if _ENGINE is None:
        _ENGINE = load(str(MODEL_PATH))
    model, processor = _ENGINE
    instruction = ('Recognize the table of the image into html format.' if task == 'table'
                   else 'Recognize the whole page content of the image.')
    prompt = apply_chat_template(processor, model.config, instruction, num_images=1)
    result = generate(model, processor, prompt, image=[Image.fromarray(image[:,:,::-1].copy())],
                      max_tokens=8192, temperature=0, verbose=False)
    if result.finish_reason == 'length' or result.generation_tokens >= 8192:
        raise ValueError('识别输出过长，结果可能不完整，请裁分单据后重试。')
    if not result.text.strip():
        raise ValueError('未识别到文字，请换一张清晰单据。')
    return result.text.strip()


def table_rows(text):
    from server import html_rows
    if len(re.findall(r'<table\b', text, re.I)) != 1 or len(re.findall(r'</table\s*>',text,re.I)) != 1:
        raise ValueError('未获得完整的单个表格，请使用一张主要表格的清晰图片。')
    table = re.search(r'<table\b[^>]*>.*?</table\s*>', text, re.I|re.S).group()
    if len(re.findall(r'<tr\b',table,re.I)) > 2000 or len(re.findall(r'<t[dh]\b',table,re.I)) > 20000:
        raise ValueError('表格尺寸超限，请裁分后重试。')
    rows = html_rows(table)
    if not rows or not any(any(cell for cell in row) for row in rows):
        raise ValueError('表格没有可识别的文字，请检查原图。')
    return rows
