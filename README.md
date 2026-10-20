# 企业 ERP 单据 OCR

图片 → 文字方向检查与自动拉正 → RapidOCR 文字识别 → TableStructureRec 表格结构识别 → 网页校对 → Excel。

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

## Windows EXE

GitHub Actions 的 **Build Windows EXE** 工作流在 Windows x64 / Python 3.12 环境打包并测试。
从成功运行的 Artifacts 下载 `ERP-OCR-Windows-x64`，解压后双击 `ERP-OCR.exe`。
程序自动打开默认浏览器；若默认浏览器无法启动，尝试直接打开已安装的 Microsoft Edge。
无页面弹出时，可把控制台第一行的 `http://127.0.0.1:端口/` 地址复制到浏览器；浏览器启动失败不终止识别服务。
保持控制台窗口开启，关闭窗口即可退出识别服务。
Python、网页资源和识别模型打包进单个 EXE，目标电脑无需安装 Python。
启动时解压模型可能需要一段时间；服务仅监听随机本机端口，不占用开发服务的 8765 端口。
当前版本未做 Windows 代码签名。

也可在 Windows x64 安装 Python 3.12 后自行构建：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-lock.txt pyinstaller==6.22.3
.venv\Scripts\python scripts/build_windows.py
.venv\Scripts\python tests/smoke_executable.py release/ERP-OCR.exe
```

输出为 `release/ERP-OCR.exe`。构建时联网下载模型；使用程序时图片不外传。
PyInstaller 要求在目标系统构建，不能直接用 macOS 生成 Windows EXE：
[PyInstaller 官方说明](https://pyinstaller.org/en/stable/operating-mode.html)。

## 检查文字方向

上传后根据 OCR 文字行的横向、纵向方向检查倾斜，不检测纸张边界，不自动裁掉图片。
文字端正时保留原图并开放识别；倾斜时自动旋转或校正轻微斜切，扩展画布保留整页。
不要求汉字、英文、数字具有相同宽高，不按字体比例任意拉伸。
未检测到清晰文字、文字方向差异过大或大幅透视时显示文字方向错误，请重新拍摄。
目前不支持通过文字框恢复严重梯形、卷曲、折痕或模糊；不生成不可靠的透视校正。
手机 EXIF 方向先统一处理，校正输出长边最多 2200 像素。
表格内部网格在逐格识别时单独拉正，不作为允许识别的前提，也不裁剪整页预览。

## 版面与表格排列

按文字坐标和表格边界区分单据抬头、列名（表头）、表体及表尾，不再固定取前四行。
规则网格逐格 OCR，保留未填写的单元格、行号及空白行，避免相邻列文字粘连。
轻微透视、外框断裂时，根据连续横线恢复内部网格，排除表外竖排联次备注，避免产生多余行列。
规则网格中没有文字的双线窄间隙合并为边框间隔；复杂或无线表格使用 TableStructureRec。
列名根据字段词识别，无法确认时保留原始表格并提示校对；不把未知内容强行改成列名。
抬头和表尾分别用“字段 / 内容”两列表格校对，可修改或增加字段，表格列名以浅绿色突出；可全部修改后导出。
Excel 汇总为一张连续表格：抬头字段动态插在明细左侧，首行是字段名、第二行填值且只填一次；明细保留原行列，表尾在底部保留字段名，内容在右侧单独分列（宽表中合并内容区域）。列宽、行高随导出调整，文本单元格保留前导零，不执行公式。
抬头优先按冒号或分隔空格拆分；OCR 粘连的订单编号、日期、供应商可自动拆分。其他字段若无法分开，可直接在字段 / 内容两列中校对后导出。
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

前端文字方向检查及失败恢复自检：`node tests/auto-correction.cjs`。
