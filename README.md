# 企业 ERP 单据 OCR

图片 → 四角透视校正 → RapidOCR 文字识别 → TableStructureRec 表格结构识别 → 网页校对 → Excel。

## 本地运行

使用 Python 3.12（本机验证为 macOS arm64）：

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python server.py
```

打开 http://127.0.0.1:8765 。点击“试用示例单据”→“开始识别”。
首次识别会从上游模型站点下载模型；下载后缓存于虚拟环境的组件目录。
服务仅监听本机，图片在内存中识别，不上传外部 OCR 服务、不写入磁盘。
不要再使用 `python3 -m http.server`：静态服务器没有识别接口。
静态网页托管也无法单独运行此版本，需要同时部署 Python 服务。

## 校正拍摄角度

上传后自动定位纸张四角，并自动生成透视校正预览，将纸面拉直为矩形。
检查预览内容完整后即可开始识别，不提供手动角点或跳过校正入口。
边界不可靠或校正失败时显示错误并停止识别，请重新拍摄或更换图片。

手机 EXIF 方向先统一处理，
校正输出长边最多 2200 像素。此方法针对平面纸张的旋转和梯形透视；纸张卷曲、
折痕、镜头畸变及模糊不能保证恢复，真实照片仍需核对预览。

## 版面与表格排列

按文字坐标和表格边界区分单据抬头、列名（表头）、表体及表尾，不再固定取前四行。
规则网格逐格 OCR，保留未填写的单元格、行号及空白行，避免相邻列文字粘连。
规则网格中没有文字的双线窄间隙合并为边框间隔；复杂或无线表格使用 TableStructureRec。
列名根据字段词识别，无法确认时保留原始表格并提示校对；不把未知内容强行改成列名。
抬头和表尾在独立文本区校对，表格列名以浅绿色突出；可全部修改后导出。
Excel 按抬头、表格、表尾排列，文本单元格保留前导零，不执行公式。
彩色日期标记与印刷表尾重叠时单独列出并提示核对，不自动充当单据日期。

## 检查

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
node tests/merge-rows.cjs
node tests/auto-correction.cjs
# 服务运行时，执行真实模型验收
node tests/smoke.cjs
# 可选：实际申请单原图路径，以及浏览器导出的 xlsx 路径
node tests/smoke.cjs /absolute/photo.jpeg /absolute/result.xlsx
```

## 范围与限制

- 支持 JPG、PNG、WebP；最大 15 MB / 2500 万像素。未支持 PDF、批量和 ERP 直接入库。
- 当前按单页一张主要表格处理；多表格、复杂跨行跨列和无明显列名的版式仍需核对。
- 模型识别结果仍需人工核对编号、数量、金额；关闭或刷新页面不会保留修改。
- 表格识别失败时显示错误，已有编辑结果保留，不生成虚构文字。
- Excel 按文本导出，等号开头的内容不执行为公式；需计算的金额可在 Excel 转成数字。
- 本地服务用于单人调试，生产部署需要专门的应用服务器、鉴权和资源控制。

## 开源依赖

通过固定版本依赖接入 [RapidAI/TableStructureRec](https://github.com/RapidAI/TableStructureRec)，
而非复制或改动上游模型源码。完整来源和许可证见 `third_party/NOTICE.md`。

前端自动校正及失败恢复自检：`node tests/auto-correction.cjs`。
