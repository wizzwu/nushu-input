# 第三方来源和署名

本工程为基于社区开源输入法的集成试用版，不代表各上游项目的官方发行或背书。

| 组件 | 固定版本/来源 | 许可 |
|---|---|---|
| 女书输入方案、读音表、OpenCC 转换表 | nushu-script/rime-nushu，详见 sources.lock.json | Unlicense |
| Unicode 女书对照数据 | nushu-script/unicode_nushu，详见 sources.lock.json | 保留上游分项许可，仅校验参考 |
| Noto Sans Nushu 字体 | nushu-script/noto-sans-nushu | SIL Open Font License 1.1 |
| 小狼毫 Weasel | rime/weasel 0.17.4 | GPL-3.0；组件保留各自许可 |
| 鼠须管 Squirrel | rime/squirrel 1.1.2 | GPL-3.0；组件保留各自许可 |
| 同文 Trime | osfans/trime v3.3.4 | GPL-3.0-or-later |
| librime | 由各平台输入法固定版本提供 | BSD-3-Clause |
| OpenCC | 由各平台输入法固定版本提供 | Apache-2.0；词库保留自身来源 |
| 朙月拼音、笔画词库、预设配置、essay | 小狼毫 0.17.4 官方发行包配套数据 | 保留词库文件中的作者、来源及原许可 |
| CPython Windows embeddable | Python 3.12.10 | Python Software Foundation License；runtime/LICENSE.txt |
| PyYAML | 6.0.3，安装器使用纯 Python 解析器 | MIT |
| NSIS | 3.11，构建工具 | zlib/libpng；各组件另有许可 |

女书输入方案作者：sgalal。字体版权：The Noto Project Authors。
平台实现及贡献者署名保留在原程序 About 和源码中。

安装器集成代码、安卓修改及构建脚本按 GPL-3.0-or-later 发布，见 LICENSE。字体及第三方数据不因此变更许可。
第三方完整许可证在安装包资源和交付目录的 licenses 中。修改后的安卓源代码包含在 NushuInput-source.tar.gz，原生源代码固定在同文 v3.3.4 对应的子模块提交。

完整获取方法：运行 `python scripts/package_delivery.py --full-native-source`，生成包含上游原生源码及其子模块的归档。
原生库复用相同版本官方 APK 的库，不混用不同版本 ABI，不重新签名或替换桌面输入法应用内部代码。
