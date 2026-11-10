# Windows 原生截图剪贴板版

这是 KDE Connect 桌面端的 fork。修改直接位于原有 `plugins/clipboard` 源码中，沿用 KDE Connect 自己的模块结构，不新增第三方插件、辅助程序或常驻进程。使用完整安装包即可，无需另行替换 DLL。

## 使用

从本仓库的 [Releases](https://github.com/finalpi/kdeconnect-kde/releases) 下载 `kdeconnect-26.08.2-native.1-windows-x64.exe`，覆盖安装到原 KDE Connect 目录。安装过程会短暂关闭 KDE Connect，保留原有配对和配置；完成后从原开始菜单快捷方式启动。

手机使用 [KDE Connect LSPosed 1.37.2-lsposed.4 或更新版本](https://github.com/finalpi/kdeconnect-android-lsposed/releases)，开启“自动同步新截图”。手机截屏后，图片会进入配对且在线电脑的图像剪贴板，可直接粘贴。目标范围沿用剪贴板同步，不需要另选电脑。

只有带 `isImage=true` 的图片剪贴板数据包会解码为图像；普通文件传输和文件剪贴板仍沿用原有行为。图片接收后清理本次传输的临时文件。传输过程中若用户复制了新内容，尚未完成的旧截图不会覆盖它；多张截图并发时以最新请求为准。图片限 50 MiB、8000 万像素。

## 构建来源

基线为 KDE Connect `v26.08.2`。当前 Windows 安装包采用**增量构建**：重新编译本 fork 的剪贴板组件，其余客户端程序、Qt 与 KDE Frameworks 使用固定 SHA-256 的官方 26.08.2 安装包。不是全量重新编译全部客户端和依赖。官方基础安装包验证发布者签名，修改后的组件和外层安装包没有商业代码签名。

安装包包含完整官方客户端和编译后的修改，离线即可安装，不要求电脑预装 KDE Connect。基础安装器保留原有卸载、右键发送、防火墙等集成。安装时会核对核心库和组件哈希，防止 ABI 混用。完整构建来源记录在安装目录的 `fork-build.json` 中。

当前匹配 Qt `6.11.1`、KDE Frameworks `6.30.0`、MSVC 2022 x64。上游 26.08.2 安装包内部将客户端版本标为 26.08.1；本 fork 的安装条目单独标为 `26.08.2-native.1`，不修改上游可执行文件的签名或版本资源。

## 本地复现

需要 Python 3.12 或更新版本、7-Zip、MSVC 2022 x64 开发环境。先准备输入：

```powershell
python packaging/windows/prepare_sdk.py --output D:/kde-pc-sdk --sevenzip "C:/Program Files/7-Zip/7z.exe"
```

在 x64 MSVC 开发者终端中执行：

```text
python packaging/windows/create_package.py --base-installer D:/kde-pc-sdk/official.exe --qt D:/kde-pc-sdk/qt --frameworks D:/kde-pc-sdk/frameworks --nsis D:/kde-pc-sdk/nsis/nsis-3.13/makensis.exe --output D:/kde-pc-output
```

脚本从干净的官方安装包提取构建运行时，不依赖构建机上已安装的 KDE Connect；从本仓库 `plugins/clipboard` 编译修改，验证原生工厂加载，并以隔离剪贴板运行图片接收、旧请求丢弃、无效图片、尺寸限制和普通文件行为测试。输出完整 EXE、`SHA256SUMS.txt` 与来源清单。GitHub Actions 执行相同流程。

也可以用上游 CMake/Craft 流程编译整个 fork，剪贴板改动已经接入原有构建目标；本仓库当前提供的 Windows 安装包采用上面说明的增量构建方法。

## 更新与恢复

以后更新本 fork 的完整安装包即可。覆盖安装官方版本会移除本 fork 的截图接收修改。基础运行时升级时需要重新匹配开发包并验证，不能把组件跨版本混用。安装前的剪贴板组件备份位于 `%LOCALAPPDATA%/kdeconnect-fork-backup-<时间>`；也可重新覆盖安装官方版本恢复。

上游版权、源码许可和依赖许可均保留。新增构建脚本和测试采用 GPL-3.0-only。
