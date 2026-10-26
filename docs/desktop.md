# 桌面分发

桌面界面使用 Python 标准库的 Tkinter/ttk 原生窗口，直接调用 `czn_deckcode.encode()` / `decode()`。没有浏览器、WebView、HTTP 服务或监听端口。

## Windows 成品

解压 `CZNDeckcode-windows-x64.zip`，双击 `CZNDeckcode.exe`。运行时完全离线，已包含所需 Python、Tcl 和 Tk。

## 构建

在 Windows 安装 Python 3.10+，在项目目录执行：

```powershell
python -m venv .venv-win
.\.venv-win\Scripts\python.exe -m pip install "pyinstaller>=6.11,<7"
.\.venv-win\Scripts\python.exe -m PyInstaller --clean --noconfirm CZNDeckcode.spec
```

自测打包文件（无须网络）：

```powershell
Start-Process -FilePath .\dist\CZNDeckcode.exe -ArgumentList '--self-test', 'desktop-check.json' -Wait
Get-Content desktop-check.json
```

自测会实际解码已知原码、重新编码/解码，并创建桌面窗口组件检查打包的 Tcl/Tk 后销毁窗口；结果写入 JSON。`frozen: true` 表示检查的是打包后的程序。

## CI

`.github/workflows/build.yml` 在 Linux Python 3.10/3.12/3.13 上检查 SDK，并在 Windows 上运行包含 GUI 的测试、构建和成品自测。Windows 成品作为 Actions artifact 上传；正式分发包在仓库 Releases。
