# 一加 Ace 5：SukiSU + SUSFS 构建包

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
- 生成 patches/ace5-susfs.patch；对固定版本的原始 24 个内核文件执行完整应用检查。
- 按 SukiSU 的实际接口适配 sucompat 的 bool 类型和 read 挂钩参数。
- 去掉当前 SukiSU builtin 不实现的上游 preinit 调用；保留该分支现有的 init.rc/ksud 启动路径。

本地验证不等于完整内核编译或实机测试。首次运行 Actions 后仍可能出现 Bazel、ABI 或工具链问题，应保留日志按错误修复。

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
