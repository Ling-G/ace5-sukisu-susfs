# 一加 Ace 5：SukiSU + SUSFS 构建包

**实机状态（2026-10-20）：第 5 次构建加入原厂模块证书后，Wi-Fi、蓝牙、声音和移动数据恢复正常。修正 boot 的 AVB 打包后，已从 boot_a 永久启动并通过普通重启；root、SUSFS v2.3.0、SELinux Enforcing 正常，用户确认解锁及上述四项功能正常。**

适用评估对象：PKG110_16.0.8.300(CN01) F.53，内核 6.1.141-android14-11。

## 如何运行

1. 将本文件夹的全部内容上传到你自己的 GitHub 仓库根目录，包含隐藏的 .github 文件夹。不要只上传 ZIP 文件本身。
2. 打开仓库 Actions，启用工作流，选择 “Ace 5 SukiSU SUSFS”，点击 Run workflow。
3. 成功后下载 Ace5-F53-SukiSU-SUSFS-experimental；若失败，下载 Ace5-build-logs 查看具体错误。

仓库地址：https://github.com/Ling-G/ace5-sukisu-susfs 。完整编译结果以 Actions 日志为准，内核仍需实机验证。
构建可能需要较长时间；仓库可见性和账号额度决定 GitHub 的计费情况。

## 产物

- Image：ARM64 未压缩内核。**它不是 boot.img，不能直接刷入 boot 分区。**
- kernel.config、System.map、build-report.json、sources.lock.json、resolved-manifest.xml、SHA256SUMS。
- ksu_susfs_arm64：使用相同 SUSFS 提交编译的用户工具。
- SUSFS-v2.3.0-userspace.zip：上游示例用户模块，包含同版本工具。先确认内核启动正常，再安装模块。

本包没有直接打包 AnyKernel3。源码是否精确对应 F.53 原厂内核仍未证明，直接做通用刷机 ZIP 会掩盖这个未验证条件。应在成功编译后用手机当前同版本的原厂 boot.img 重打包，核对镜像头、安全补丁和活动槽位。保留原厂镜像及恢复路径。

## 已完成的本地检查

- 拉取并固定一加 common、SukiSU builtin、SUSFS 源码。
- 实际发现并解决原版 SUSFS 补丁在 Ace 5 源码上的五处上下文冲突。
- 生成 patches/ace5-susfs.patch；对固定版本的原始 25 个内核文件执行完整应用检查。
- 按 SukiSU 的实际接口适配 sucompat 的 bool 类型和 read 挂钩参数。
- 修复完整编译发现的三个 SELinux 未定义接口；使用 SUSFS 上一提交的自包含实现，详见 patches/README.md。
- 去掉当前 SukiSU builtin 不实现的上游 preinit 调用；保留该分支现有的 init.rc/ksud 启动路径。

第 5 次 Actions 已完成完整编译，设备验证范围见下文；后续修改仍需重新验证。

## 首版范围

启用 SukiSU 和 SUSFS v2.3.0；关闭 KPM、KSU_DEBUG。保留原厂 CFI、SELinux、符号与签名保护策略。
不叠加 ZRAM 算法或额外补丁，不修改 init_boot、vbmeta 或双槽位。
SUSFS 不是 APK 安装选项，仅安装用户模块不能让原厂内核获得 SUSFS。

## 构建约束

- 固定源码提交和 NDK 版本记录在 sources.lock.json。
- manifests/ace5.xml 基于一加官方 oneplus_ace5_b.xml，三个一加项目均固定到完整提交。
- patches/ace5-susfs.patch **替代**所固定 SUSFS 仓库中的原始内核补丁；不得先应用原补丁再应用它。
- SukiSU builtin 已包含它自己的 SUSFS 集成，不再套用 SUSFS 中面向官方 KernelSU 的 10_enable_susfs_for_ksu.patch。
- 补丁失败即停止；不使用忽略失败的处理。对原厂保护策略导致的错误也先停止，按日志分析。
- 构建后从实际 Image 解出配置，确认 SUSFS 启用、KPM 关闭、CFI/SELinux/MODVERSIONS 保留，并检查链接符号。
- 工作流中的磁盘清理只允许运行在 GitHub 托管 runner，且在 SUSFS 工具编译后进行。

## 实机验收

手机版本、uname -r、Bootloader 解锁状态和原厂镜像必须先核实。首启成功后测试 root 授权、重启、Wi-Fi、蓝牙、相机、指纹、充电和休眠，再测试 SUSFS 用户模块。SUSFS 不保证所有应用检测或设备完整性认证通过。

## 上游与许可

- 一加官方源码：https://github.com/OnePlusOSS/kernel_manifest
- SukiSU builtin：https://github.com/SukiSU-Ultra/SukiSU-Ultra/tree/builtin
- SUSFS：https://gitlab.com/simonpunk/susfs4ksu

补丁含 GPL-2.0 内核衍生代码，见 patches/LICENSE。新写的构建辅助脚本采用 MIT，见 LICENSE。

## 原厂模块信任修复

第 4 次构建的日志显示原厂 rfkill 等 GKI 模块被 protected export 校验拒绝，Wi-Fi/蓝牙依赖模块因此加载失败。重建时通过 CONFIG_SYSTEM_TRUSTED_KEYS 加入 F.53 原厂 boot 中提取的公开 X.509 证书，并保留本次构建自身的签名密钥及 MODULE_SIG_PROTECT。已用该公开证书实际验证原厂 rfkill 模块 CMS 签名，证书来源和摘要见 certs/provenance.json；不含私钥。collect.py 将从实际 Image 检查证书存在，第 5 次构建的四项基础功能已实机复测通过。

管理器需要 UAPI 6：正式版 v4.2.1_40994 是 UAPI 5，会提示更新管理器。已用官方 CI v4.2.1_41027 验证 root 和 SUSFS 正常： https://github.com/SukiSU-Ultra/SukiSU-Ultra/actions/runs/39278592599 。

## boot 打包修复与复现

旧的 36 MB experimental boot 缺少 AVB 尾部：临时启动成功不能代表永久刷写可用。原厂 vbmeta 将 boot 作为链式验证分区。当前已验证镜像为 192 MiB，内核与第 5 次构建相同，重新生成 boot 哈希、VBMeta 和 AVB footer，实机永久启动及普通重启通过。

```sh
python scripts/repack_boot.py --stock-boot /path/to/F53/boot.img --kernel /path/to/Image --output /path/to/boot-F53-SukiSU-SUSFS-avbfix.img
```

脚本只接受已核验的 F.53 原厂 boot，使用固定提交的 AOSP 工具，校验头部、内核与 AVB 哈希后输出镜像和 JSON 报告。算法 NONE 仅适用于已解锁设备，不是 OEM 签名，不修改 vbmeta 分区。与第 5 次 Image 配合，输出 SHA256 为 `66598cf3862726ce90e2e55b555b68215a8d3e3c6202ac17199751dd832de1be`，与实机 boot_a 回读及已验证修正版一致。原厂 boot 不上传仓库，请自行保留匹配固件和恢复备份。

固定工具来源见 tools/bootimg/provenance.json；AOSP 工具保留 Apache-2.0 文件头。打包脚本通过实际生成、官方 AVB 校验及逐字节一致性验证。详见 reference/device-validation-avbfix.json。无需重新编译内核即可修正此次打包问题。

已知限制：oplus_bsp_game_opt 缺少 4 个旧 android_vh_scx tracepoint，游戏优化兼容性仍未完成；相机、指纹、充电和休眠未完成全面验收。SUSFS 用户模块尚未安装，内核接口验证通过不代表所有应用检测或完整性认证通过。
