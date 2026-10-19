#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import zlib

workspace = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
package = Path(__file__).resolve().parents[1]
lock = json.loads((package / 'sources.lock.json').read_text())
dist = workspace / 'kernel_platform/out/msm-kernel-pineapple-gki/dist'
image = dist / 'Image'
if not image.is_file():
    raise SystemExit('Expected uncompressed kernel Image not found: ' + str(image))
raw = image.read_bytes()
if raw[56:60] != b'ARMd':
    raise SystemExit('Not an ARM64 Linux Image')
start = raw.find(b'IKCFG_ST')
end = raw.find(b'IKCFG_ED', start)
if start < 0 or end < 0:
    raise SystemExit('Embedded kernel configuration missing')
config = zlib.decompress(raw[start+8:end], wbits=31).decode()
required = ['KSU', 'KSU_SUSFS', 'KSU_SUSFS_SUS_PATH', 'KSU_SUSFS_SUS_MOUNT',
            'KSU_SUSFS_SUS_KSTAT', 'KSU_SUSFS_SPOOF_UNAME', 'KSU_SUSFS_ENABLE_LOG',
            'KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS', 'KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG',
            'KSU_SUSFS_OPEN_REDIRECT', 'KSU_SUSFS_SUS_MAP', 'CFI_CLANG', 'MODVERSIONS',
            'SECURITY_SELINUX']
for name in required:
    if 'CONFIG_' + name + '=y' not in config.splitlines():
        raise SystemExit('Missing enabled feature in actual Image: CONFIG_' + name)
if 'CONFIG_KPM=y' in config.splitlines() or 'CONFIG_KSU_DEBUG=y' in config.splitlines():
    raise SystemExit('Unexpected KPM/debug activation')
match = re.search(rb'Linux version (6\.1\.141-android14-11[^\x00\r\n]*)', raw)
if not match:
    raise SystemExit('Unexpected built kernel version/KMI')
symbols = dist / 'System.map'
if not symbols.is_file():
    raise SystemExit('System.map missing; cannot verify SukiSU and SUSFS linkage')
symbol_text = symbols.read_text()
for name in ['kernelsu_init', 'susfs_init', 'ksu_handle_execveat', 'ksu_handle_setresuid']:
    if not re.search(r'\b' + name + r'$', symbol_text, re.M):
        raise SystemExit('Required linked symbol missing: ' + name)
out.mkdir(parents=True, exist_ok=True)
shutil.copy2(image, out / 'Image')
shutil.copy2(symbols, out / 'System.map')
(out / 'kernel.config').write_text(config)
shutil.copy2(package / 'sources.lock.json', out / 'sources.lock.json')
report = {'status': 'compiled-and-statically-checked; not device-tested',
          'target_firmware': lock['firmware'], 'banner': match.group(0).decode(errors='replace'),
          'susfs_version': lock['susfs_version'], 'kpm': False,
          'note': 'Source branch has not been proven identical to the F.53 stock kernel commit.'}
(out / 'build-report.json').write_text(json.dumps(report, indent=2) + '\n')
notes = '''这是编译并静态检查的内核，尚未经过 Ace 5 实机验证。
Image 不是 boot.img，不能直接刷入 boot 分区。
应以当前手机同版本的原厂 boot.img 为基础重打包，并保留原厂恢复镜像。
SUSFS 用户模块须在确认内核正常启动后安装；仅安装模块不能为原厂内核添加 SUSFS。
本构建不修改 init_boot、不关闭 SELinux，也没有集成 KPM。
'''
(out / '使用前必读.txt').write_text(notes, encoding='utf-8')
checksums = []
for file in sorted(out.iterdir()):
    if file.is_file() and file.name != 'SHA256SUMS':
        checksums.append(hashlib.sha256(file.read_bytes()).hexdigest() + '  ' + file.name)
(out / 'SHA256SUMS').write_text('\n'.join(checksums) + '\n')
print(json.dumps(report, indent=2))
