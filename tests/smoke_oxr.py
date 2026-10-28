"""Real local GPU smoke check; run separately from unit tests."""
import json
import sys
from pathlib import Path
import cv2
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import recognize, align
root=Path(__file__).resolve().parents[1]
image=cv2.imread(str(root/'tests/fixtures/example-purchase-order.png'))
aligned, info=align(image)
print('alignment', info, flush=True)
result=recognize(aligned)
print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
flat=' '.join(cell for row in result['rows'] for cell in row)
assert 'A001' in flat and '700.00' in flat, flat
assert any('订单编号' in line for line in result['header']),result['header']
assert any('1250' in line for line in result['footer']),result['footer']
assert result['header_rows']==1, result['rows']
assert len(result['rows'])==4, result['rows']
assert result['engine']=='SoMark OXR-1.0 / MLX'
print('PASS: local OXR table, leading-zero identifiers, header and footer',flush=True)
