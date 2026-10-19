# Ace 5 SUSFS 补丁来源

基于 simonpunk/susfs4ksu 的 gki-android14-6.1 提交 f6c046775c0a14834748cc82c03f1d1b0285c206，内核补丁由上游作者提供。

本地适配：保留一加 PGO 和连续页调试改动，调整五处上下文；匹配 SukiSU builtin 的 bool sucompat 开关和三参数 read 挂钩；移除该分支尚未实现的上游 preinit 路径。使用当前 builtin 自身的 init.rc/ksud 启动逻辑。

本文件替代上游 50_add_susfs_in_gki-android14-6.1.patch。不要重复应用。适用 common 提交 34d0b26abc5f76a488eca6c77ac992f3d8fb68f9；需配合同包锁定的 SukiSU 和 SUSFS 头文件、fs/susfs.c。许可 GPL-2.0。

SELinux 兼容：f6c0467 改为调用官方 KernelSU 的 my_write_context / my_write_access / my_setprocattr，而固定的 SukiSU builtin 未提供这些接口。仅这部分恢复使用 SUSFS 上一提交 049e7b8a2828f3e1d698c2aa9a0792024d0f2e37 的三文件实现（hooks.c、selinuxfs.c、ss/services.c），其余 SUSFS 源码和用户工具保持 f6c0467。保留真实策略的权限检查，补齐上下文到 SID 的兼容函数。prepare.py 会在编译前检查这些接口。
