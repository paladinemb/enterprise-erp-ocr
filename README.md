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

## 表格排列

沿用单据的前四行作为左侧四组信息，标题在首行，值在第二行填写一次，
后续行留空。单据信息下方的表格由 TableStructureRec 自动选择有线或无线
识别模型，得到的单元格结构放在右侧。合并单元格展开为普通网格，内容仅
保留于左上角，其他格留空。Excel 与当前页面网格一致，文本格式保留前导零。

示例的前四列验收标准保存在 `tests/fixtures/expected-first-four.json`，
对应人工截图为 `manual-first-four-columns.png`，原图为 `example-purchase-order.png`。
示例双语标题按人工结果整理为“采购订单”与“PURCHASEORDER”。

## 检查

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
node tests/merge-rows.cjs
# 服务运行时，执行真实模型验收；可附带浏览器下载的 xlsx 路径
node tests/smoke.cjs
```

## 范围与限制

- 支持 JPG、PNG、WebP；最大 15 MB / 2500 万像素。未支持 PDF、批量和 ERP 直接入库。
- 当前业务版式要求前四行是单据信息、下方是一张表格；其他版式需调整字段定位。
- 模型识别结果仍需人工核对编号、数量、金额；关闭或刷新页面不会保留修改。
- 表格识别失败时显示错误，已有编辑结果保留，不静默退回旧的坐标分列算法。
- Excel 按文本导出，等号开头的内容不执行为公式；需计算的金额可在 Excel 转成数字。
- 本地服务用于单人调试，生产部署需要专门的应用服务器、鉴权和资源控制。

## 开源依赖

通过固定版本依赖接入 [RapidAI/TableStructureRec](https://github.com/RapidAI/TableStructureRec)，
而非复制或改动上游模型源码。完整来源和许可证见 `third_party/NOTICE.md`。

前端自动校正及失败恢复自检：`node tests/auto-correction.cjs`。
