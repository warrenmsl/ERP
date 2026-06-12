# Windows 转化说明（给你自己在 Win 本上操作）

你收到的是 Mac 打的 **erp录入工具-待转Win.zip**（小文件，约 3~8MB）。

## 步骤

1. 解压到英文路径，例如 `C:\erp-build`
2. 安装 Python 3.10+，安装时勾选 **Add to PATH**
3. 双击 **转换并打包.bat**
4. 等待 5~15 分钟（下载 Windows 依赖 + Chromium）
5. 完成后得到 `dist\erp录入工具-win.zip`
6. 把 **erp录入工具-win.zip** 发给同事

同事解压后双击 **安装并启动.bat** 即可，无需再打包。

## 若 bat 被拦截

右键 **转换并打包.bat** → 以管理员身份运行，或在 PowerShell 中执行：

```powershell
cd C:\erp-build
powershell -ExecutionPolicy Bypass -File scripts\pack_erp_standalone_win.ps1
```
