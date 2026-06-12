# ERP 录入工具

这是 ERP 录入工具的服务器部署版。业务代码已恢复为原始版本，仓库只新增部署启动文件，不包含 Windows 便携运行时、Chromium 下载目录、登录态和本地数据库。

## Docker 部署

```bash
docker compose up -d --build
```

启动后访问：

```text
http://服务器IP:8001
```

首次自动上传时需要在弹出的浏览器登录 ERP。登录态会保存在服务器本地的 `config/erp_storage.json`，不要提交到仓库。

## 本地运行

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
python main_erp.py
```

默认端口是 `8001`。服务器部署时使用 `HOST=0.0.0.0`，本地调试可以使用默认值。
