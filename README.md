# 女书输入法

输入英文字母拼音，选择候选，输出标准 Unicode 女书字符。支持普通话拼音、江永方言拼音及原方案的 396 个女书字符；内置输入法程序、词典和 Noto Sans Nushu 字体，安装与首次部署无需联网。

## 下载安装

当前版本：**0.1.0 试用版**。请按设备选择一个安装包。

| 平台 | 下载安装包 | 适配目标 |
|---|---|---|
| Windows | [NushuInput-Setup.exe](https://github.com/wizzwu/todo/releases/download/v0.1.0-trial/NushuInput-Setup.exe) | Windows 10/11，Intel/AMD 64 位 |
| macOS | [NushuInput.pkg](https://github.com/wizzwu/todo/releases/download/v0.1.0-trial/NushuInput.pkg) | macOS 13+，Intel / Apple Silicon |
| 安卓 | [NushuInput.apk](https://github.com/wizzwu/todo/releases/download/v0.1.0-trial/NushuInput.apk) | Android 8+，ARM 32/64 位 |

[查看发布页面及所有文件](https://github.com/wizzwu/todo/releases/tag/v0.1.0-trial) · [下载完整交付包](https://github.com/wizzwu/todo/releases/download/v0.1.0-trial/NushuInput-delivery.zip) · [SHA-256 校验清单](https://github.com/wizzwu/todo/releases/download/v0.1.0-trial/SHA256SUMS.txt)

## 安装后怎么用

1. 安装对应文件，按系统提示授权并启用输入法；Mac 安装后需要退出账户并重新登录。
2. 选择“女书·普通话拼音”，输入拼音后选字。另提供江永方言方案。
3. 安卓点击“汉/女”键切换；桌面普通话方案按 `Ctrl+Shift+4` 切换汉字／女书。

完整步骤、配置备份和错误日志位置见[使用说明](docs/使用说明.txt)。候选栏内置字体；复制到其他应用后能否显示女书，取决于目标应用的字体支持。

## 试用版验证状态

| 平台 | 已验证 | 尚未完成 |
|---|---|---|
| Windows | 云端构建、文件完整性、隔离输入引擎测试 | 干净系统完整安装及桌面使用验收 |
| macOS | 临时 macOS 15 ARM64 环境系统安装、用户配置部署、396 字输入引擎测试 | 真实桌面会话、Intel 及 macOS 13 安装验收 |
| 安卓 | 断网模拟器安装、首次部署、输入、切换、复制及覆盖安装 | 实体手机、Android 8 实机、16KB 内存页设备 |

桌面安装器未做商业签名或苹果公证。当前版本供试用，尚不能承诺所有适配目标都已安装即用。详见[验证记录](docs/验证记录.md)及[测试报告目录](reports/README.md)。

## 资料与源码

| 资料 | 内容 |
|---|---|
| [使用说明](docs/使用说明.txt) | 安装、启用、输入、备份及故障日志 |
| [验证记录](docs/验证记录.md) | 已测内容与未验证范围 |
| [开发与构建](docs/开发与构建.md) | 本地构建、自动构建、安卓签名及工程目录 |
| [第三方来源与许可](THIRD_PARTY_NOTICES.md) | 上游项目、组件版本及许可证 |
| [固定来源清单](sources.lock.json) | 上游提交编号与下载校验值 |

本仓库保留复现构建及维护所需的源码和测试。Releases 中另附修改源码、对应原生源码和完整交付包；普通用户只需下载自己平台的安装包。

基于 [rime-nushu](https://github.com/nushu-script/rime-nushu)、[unicode_nushu](https://github.com/nushu-script/unicode_nushu)、[Noto Sans Nushu](https://github.com/nushu-script/noto-sans-nushu)，平台程序采用小狼毫、鼠须管和同文输入法。本项目为社区开源组件的集成试用版，各组件保留其原许可与署名。
