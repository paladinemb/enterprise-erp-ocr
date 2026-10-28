# 企业 ERP 单据 OCR · SoMark OXR

在 Apple Silicon Mac 上用 **SoMark OXR-1.0 + MLX** 将单据图片转换成可编辑表格，再导出 Excel。图片在本机内存中识别，不调用远程 OCR API。

## 本机安装

需要 Apple Silicon、macOS 26+、Python 3.12。此分支已替换旧 RapidOCR / TableStructureRec 引擎；旧 Windows EXE 不包含 OXR，当前版本不再构建 Windows EXE。

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
# hf CLI: https://huggingface.co/docs/huggingface_hub/guides/cli
hf download SoMarkAI/OXR-1.0 \
  --revision c708407f9d2b4df658f2543d9132b62bb7221df4 \
  --exclude 'layout_analysis/*' 'plugins/*' 'modeling_oxr.py' 'configuration_oxr.py' \
  --local-dir models/OXR-1.0
.venv/bin/python desktop.py
```

已有同一版本权重时无需重复下载：设置 `OXR_MODEL_PATH=/absolute/path/OXR-1.0`，再启动程序。模型约 3 GB，不提交到 Git。MLX-VLM 使用固定源码版本 `230fc308efb577d87446306bfb8a3e9f1a129558`；依赖文件没有锁定全部传递依赖。

也可用 `.venv/bin/python server.py` 启动固定端口服务，打开 `http://127.0.0.1:8765`。双击页面中的“试用示例单据”即可测试。依赖和权重准备完成后，识别过程无需联网。首次识别需加载模型。

## 处理与校对

- 上传 JPG、PNG 或 WebP，限制 15 MB / 2500 万像素；手机 EXIF 方向先统一处理。
- 用 OpenCV 文字行形态估计倾斜，沿用不裁纸边的校正；方向不可靠时拒绝自动拉正。此步骤不再使用旧 OCR 检测模型，严重透视、竖排文字及模糊图片需重新拍摄。
- OXR 分别执行整页文字识别、HTML 表格识别；保留空单元格及跨行跨列占位。只接受完整的单个表格，输出截断或无法识别时显示错误。
- 抬头与表尾依据字段标签分段，表格中相同的独占行去重；未集成官方独立布局模型，对复杂版式的分区没有保证。完整文字保留在文本区，可校对后导出。
- 本机模型不返回旧 RapidOCR 的逐字置信度。编号、数量、金额及未填写的单元格都应与原图核对。
- 保留网页字段编辑、增行增列、Excel 导出和前导零；Excel 单元格按文本写入，不执行公式。刷新页面不保留编辑结果。

支持单页主要表格；不支持 PDF、批量或 ERP 直接入库。模型可能遗漏、重复或生成错误内容；本机适配不等同于官方完整布局流水线。本地服务仅监听回环地址，用于单人使用。

## 验证

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
node tests/merge-rows.cjs
node tests/auto-correction.cjs
# 真实 Apple GPU 验收（需要权重和 MLX）
.venv/bin/python tests/smoke_oxr.py
```

普通单元测试不下载模型，不要求 GPU。`tests/smoke_oxr.py` 验证本机 OXR 的抬头、表格和合计输出。

## 许可证

应用源码采用 [MIT](LICENSE)。OXR 权重采用 [OXR License](third_party/OXR-LICENSE)，不是无限制的 Apache-2.0：其商业授权门槛、对第三方在线服务的署名和竞争性托管 API 限制见原文。MLX-VLM / MLX、OpenCV、Pillow、NumPy、SheetJS 等组件分别遵循各自许可证，见 [第三方说明](third_party/NOTICE.md)。

模型来源：[SoMarkAI/OXR-1.0](https://huggingface.co/SoMarkAI/OXR-1.0)。推理适配：[MLX-VLM OXR](https://github.com/Blaizzy/mlx-vlm/tree/230fc308efb577d87446306bfb8a3e9f1a129558/mlx_vlm/models/oxr)。
