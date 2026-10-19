#!/usr/bin/env bash
set -euo pipefail
PACKAGE=$(cd "$(dirname "$0")/.." && pwd)
ADDONS=$1
NDK_ROOT=$2
VERSION=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["ndk_version"])' "$PACKAGE/sources.lock.json")
test -x "$NDK_ROOT/ndk-build"
grep -q "$VERSION" "$NDK_ROOT/source.properties"
cd "$ADDONS/susfs/ksu_susfs"
"$NDK_ROOT/ndk-build" -j2 APP_ABI=arm64-v8a APP_PLATFORM=android-26
install -m 755 libs/arm64-v8a/ksu_susfs "$PACKAGE/output/ksu_susfs_arm64"
cp libs/arm64-v8a/ksu_susfs "$ADDONS/susfs/ksu_module_susfs/tools/ksu_susfs_arm64"
cd "$ADDONS/susfs"
# Module zip entries must be rooted at module.prop, not at a parent directory.
cd ksu_module_susfs
zip -r "$PACKAGE/output/SUSFS-v2.3.0-userspace.zip" . >/dev/null
