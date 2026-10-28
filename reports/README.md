# 测试报告目录

面向使用者的汇总请先阅读[验证记录](../docs/验证记录.md)。以下文件保留检查依据，构建成功与实际安装、人工使用测试分别记录。

| 类别 | 文件 | 说明 |
|---|---|---|
| 字符与读音 | [data-validation.json](data-validation.json) | 396 字、字体覆盖及 8 处上游读音差异 |
| 安装包结构 | [package-validation.json](package-validation.json) | Mac 归档、安卓 ABI 与资源检查 |
| Mac 安装 | [macos-cloud-verification.json](macos-cloud-verification.json) | 临时 Mac 系统安装与部署结果及对应文件校验值 |
| Mac 输入 | [rime-smoke-native-macos.json](rime-smoke-native-macos.json) | Mac 原生引擎输入检查 |
| Windows 输入 | [固定 x86 引擎](rime-smoke-pinned-0.17.4-x86.json)、[本机 x64 引擎](rime-smoke-installed-0.17.3-x64.json)、[稳定接口检查](rime-smoke-stable-api-x64.json) | 隔离目录中的输入检查，不等于完整 Windows 安装验收 |
| 安卓离线使用 | [android-offline-verification.json](android-offline-verification.json) | 模拟器环境、输入、复制与覆盖安装结果 |
| 安卓截图 | [候选栏](android-candidates.png)、[输出结果](android-offline.png) | 最终签名 APK 的模拟器测试截图 |
| 安卓身份与签名 | [android-package-info.txt](android-package-info.txt)、[android-signature.txt](android-signature.txt) | 应用标识、ABI 及签名证书检查 |
| 安卓原生源码 | [android-native-source-commits.txt](android-native-source-commits.txt) | 对应原生子模块提交 |

各平台的 `*-cloud-artifact.json` 记录云端构建产物来源，`*-cloud-resource-manifest.json` 记录实际资源及校验值。安装包与源码下载请前往[试用版发布页面](https://github.com/wizzwu/todo/releases/tag/v0.1.0-trial)。
