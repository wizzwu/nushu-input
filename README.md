# 女书输入法：三平台离线安装工程

输入英文字母拼音，选择女书候选，输出标准 Unicode 女书字符。包含普通话拼音和江永方言拼音，支持原项目的 396 个女书字符。

| 平台 | 产物 | 目标设备 |
|---|---|---|
| Windows | `dist/NushuInput-Setup.exe` | Windows 10/11，Intel/AMD x64 |
| macOS | `dist/NushuInput.pkg` | macOS 13+，Intel/Apple Silicon |
| Android | `dist/NushuInput.apk` | Android 8+，ARM32/ARM64 合并包 |

完整安装与首次部署无需联网。系统授权、启用键盘、添加输入法需要用户确认。
桌面安装器未购买商业签名或苹果公证，适用于小范围试用。
安装包存在不等于通过真机验证，具体结果见 `docs/验证记录.md`。

## 构建

环境：Python 3.12+、Git、curl、7-Zip；安卓另需 JDK 17、Android SDK 35、Build Tools 35.0.0。

```text
python -m pip install -r requirements.txt
python scripts/prepare.py
python scripts/validate.py
python -m unittest discover -s tests
python scripts/build_windows.py         # Windows，自动解压固定版本 NSIS
python scripts/build_android.py         # Windows/Linux/macOS
python scripts/build_macos.py           # macOS，使用 pkgbuild/productbuild
python scripts/package_delivery.py
```

构建时需要联网下载固定版本依赖，安装时不需要。`sources.lock.json` 固定源码提交和下载校验值；`resource-manifest.json` 固定实际装入的资源。修改方案后必须重新验证。

安卓从同文 v3.3.4 的 Kotlin/Java 源码编译，保留 JNI 类命名空间，修改应用标识为 `org.nushuinput.trial`。
原生库从相同版本官方 APK 中提取，两个 ABI 使用同一套源码版本；不修改原生库。
这样避免为本次数据和界面适配重新编译庞大的原生依赖。原生库源码版本由上游 tag 的子模块提交固定。
如需从头构建原生库，使用 `python scripts/package_delivery.py --full-native-source` 获取并附带对应源代码。

## GitHub Actions

工作流 `.github/workflows/build.yml` 在 Windows、Linux、macOS 分别构建，产物保存在 Actions Artifacts，不自动创建公开 Release。
Mac 产物用系统工具展开，检查 Intel/ARM64 架构和应用签名；该检查不能代替真机安装。

若只有 Windows，可使用 `python scripts/build_macos.py --portable` 生成未签名的标准 XAR 安装包，原样保留鼠须管组件的应用内容，并检查归档校验、脚本和架构。
该方法不等于经过 macOS Installer 验证；本次便携构建包的状态必须与原生构建分别记录。

首次配置 Android Actions 时需设置以下仓库 Secrets，必须与本地签名相同：

- `NUSHU_KEYSTORE_BASE64`：签名文件 Base64 内容。
- `NUSHU_STORE_PASSWORD`、`NUSHU_KEY_PASSWORD`、`NUSHU_KEY_ALIAS`。

本地首次构建自动创建试用签名，保存在用户目录 `.codex/secrets/nushu-input`，并备份到其 `backup` 子目录；不进入源码或交付压缩包。
CI 缺少签名时直接失败，禁止生成新密钥，以免后续 APK 无法覆盖升级。
不要把签名密码或密钥写入工作流、提交或日志。

## 数据与许可

- 女书方案：[nushu-script/rime-nushu](https://github.com/nushu-script/rime-nushu)，Unlicense。
- 对照数据：[nushu-script/unicode_nushu](https://github.com/nushu-script/unicode_nushu)，用于校验并生成差异报告，首版不改原映射。
- 字体：[nushu-script/noto-sans-nushu](https://github.com/nushu-script/noto-sans-nushu)，SIL OFL 1.1。
- Windows：[rime/weasel](https://github.com/rime/weasel) 0.17.4；macOS：[rime/squirrel](https://github.com/rime/squirrel) 1.1.2。
- Android：[osfans/trime](https://github.com/osfans/trime/tree/v3.3.4)，GPL-3.0-or-later；安卓修改和构建脚本按同一许可证提供。
- 原始词库、OpenCC 字典及第三方组件保留各自许可。不得把整个工程统一标成 Unlicense。

为兼容 2020 年女书方案，公共依赖采用固定小狼毫发行包附带的朙月拼音配置；不直接替换成修改过简繁转换开关的新版本。
候选栏内置字体；跨应用的显示由目标应用字体决定。输出字符不使用汉字码位伪装，不加入私用区替代编码。

用户说明：`docs/使用说明.txt`。测试报告和完整来源清单随构建产物交付。

安卓当前原生库来自同文 v3.3.4，已在 4KB 内存页环境测试；16KB 内存页设备尚未验证，不能承诺全部较新安卓机型均可用。
