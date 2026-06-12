# ERP 录入工具（独立版）

支持粘贴表格、上传 Excel、截图 OCR，并可在网页中预览映射后自动上传。

## Windows 成品包使用

1. 解压 `erp录入工具-win.zip` 到任意目录，例如 `D:\ERPTool`
2. 双击 `安装并启动.bat`
3. 浏览器打开 [http://127.0.0.1:8001](http://127.0.0.1:8001)
4. 日常使用时直接双击 `启动 ERP.bat`

说明：

- 成品包已自带 Python 运行时、Python 依赖和 Playwright Chromium
- 接收方机器不需要额外安装 Python
- 首次自动上传时，会弹出浏览器登录 ERP 站点，请使用自己的账号登录

## 截图 OCR

截图 OCR 在 Windows 上依赖 Tesseract OCR。

- 推荐安装 [UB Mannheim Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
- 安装时勾选中文语言包
- 程序会自动探测常见安装路径

如果不使用截图 OCR，也可以只使用粘贴表格或上传 Excel。

## 通知开关

默认关闭钉钉通知。若需开启，编辑 `scripts/erp_standalone_start_win.bat`，把 `NOTIFY_ERP_AUTO=0` 改为 `1`，并配置对应环境变量。

## 配置文件

- `config/erp_rpa.local.json`：ERP RPA 本地配置，首次启动会从 `.example` 自动复制
- `config/erp_storage.json`：上传登录态缓存，首次登录后自动生成，请勿外传
