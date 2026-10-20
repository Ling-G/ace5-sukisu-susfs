#!/usr/bin/env python3
"""Integrate a pinned SukiSU/SUSFS pair into the pinned Ace 5 common tree."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import ssl
import subprocess

PACKAGE = Path(__file__).resolve().parents[1]
LOCK = json.loads((PACKAGE / 'sources.lock.json').read_text())

def run(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()

def require(condition, message):
    if not condition:
        raise SystemExit(message)

def write(path, text):
    path.write_text(text, encoding='utf-8', newline='\n')

def replace_one(text, old, new):
    require(text.count(old) == 1, 'Unexpected source context: ' + old[:100])
    return text.replace(old, new, 1)

def prepare(workspace, addons):
    common = workspace / 'kernel_platform/common'
    suki = addons / 'SukiSU'
    susfs = addons / 'susfs'
    for tree, key in [(common, 'common'), (workspace / 'kernel_platform/msm-kernel', 'msm'),
                      (workspace, 'modules'), (suki, 'sukisu'), (susfs, 'susfs')]:
        require(run('git', 'rev-parse', 'HEAD', cwd=tree) == LOCK['sources'][key],
                'Source commit mismatch: ' + key)
    mf = (common / 'Makefile').read_text()
    for setting, expected in [('VERSION', '6'), ('PATCHLEVEL', '1'), ('SUBLEVEL', '141')]:
        require(re.search(r'^' + setting + r'\s*=\s*' + expected + r'\s*$', mf, re.M),
                'Unexpected kernel version')
    header = (susfs / 'kernel_patches/include/linux/susfs.h').read_text()
    require('#define SUSFS_VERSION "v2.3.0"' in header, 'Unexpected SUSFS version')
    patch = PACKAGE / 'patches/ace5-susfs.patch'
    subprocess.run(['git', 'apply', '--check', str(patch)], cwd=common, check=True)
    subprocess.run(['git', 'apply', str(patch)], cwd=common, check=True)
    for folder in ['fs', 'include/linux']:
        src = susfs / 'kernel_patches' / folder
        for file in src.iterdir():
            if file.is_file():
                shutil.copy2(file, common / folder / file.name)
    # Fail before a long build if the SUSFS patch expects unavailable KSU APIs.
    selinux_sources = '\n'.join((common / 'security/selinux' / f).read_text()
                                 for f in ['hooks.c', 'selinuxfs.c', 'ss/services.c'])
    for symbol in ['my_write_context', 'my_write_access', 'my_setprocattr']:
        require(not re.search(r'\b' + symbol + r'\s*\(', selinux_sources),
                'Incompatible upstream KernelSU-only SELinux interface: ' + symbol)
    services = (common / 'security/selinux/ss/services.c').read_text()
    for symbol in ['my_security_context_to_sid', 'my_security_context_str_to_sid']:
        require(re.search(r'^int ' + symbol + r'\s*\([^;]+?\)\s*\{', services, re.M),
                'Missing SELinux compatibility implementation: ' + symbol)
    dest = workspace / 'kernel_platform/SukiSU'
    require(not dest.exists(), 'Integration destination already exists')
    shutil.copytree(suki, dest, ignore=shutil.ignore_patterns('.git'))
    # The pinned upstream Makefile otherwise obtains version metadata over the network.
    makefile = dest / 'kernel/Makefile'
    text = makefile.read_text()
    text = re.sub(r'^\$\(shell cd \$\(KSU_SRC\).*fetch --unshallow.*\)\s*$', '', text, flags=re.M)
    text = re.sub(r'^KSU_GITHUB_VER\s*:=.*$', 'KSU_GITHUB_VER := 4.2.1', text, flags=re.M)
    text = re.sub(r'^GITHUB_COMMITS\s*:=.*$', 'GITHUB_COMMITS := ' + str(LOCK['sukisu_commit_count']), text, flags=re.M)
    text = re.sub(r'^LOCAL_COUNT\s*:=.*$', 'LOCAL_COUNT := ' + str(LOCK['sukisu_commit_count']), text, flags=re.M)
    text = re.sub(r'^KSU_VERSION_FULL\s*:=.*$',
                  'KSU_VERSION_FULL := v4.2.1-builtin-5ef32ad5-susfs2.3.0', text, flags=re.M)
    write(makefile, text)
    link = common / 'drivers/kernelsu'
    require(not link.exists() and not link.is_symlink(), 'Existing root integration found')
    link.symlink_to('../../SukiSU/kernel', target_is_directory=True)
    require(link.resolve() == dest / 'kernel', 'Incorrect integration symlink')
    drivers_make = common / 'drivers/Makefile'
    write(drivers_make, drivers_make.read_text() + '\nobj-$(CONFIG_KSU) += kernelsu/\n')
    drivers_cfg = common / 'drivers/Kconfig'
    text = drivers_cfg.read_text()
    pos = text.rfind('endmenu')
    require(pos >= 0, 'drivers/Kconfig menu not found')
    write(drivers_cfg, text[:pos] + 'source "drivers/kernelsu/Kconfig"\n\n' + text[pos:])
    # Retain trust in the F.53 stock GKI modules alongside our build's signing key.
    stock_cert = (PACKAGE / 'certs/ace5-stock-module-cert.pem').read_text()
    stock_der = ssl.PEM_cert_to_DER_cert(stock_cert)
    require(hashlib.sha256(stock_der).hexdigest() == '5412f448880df61ebddd15398b7bf11e223cb96a266fb2ccc6152285e073b7ab',
            'Unexpected F.53 module trust certificate')
    write(common / 'certs/ace5-stock-module-cert.pem', stock_cert)
    # Set only feature options; keep the OEM security, CFI and export policies.
    config = common / 'arch/arm64/configs/gki_defconfig'
    enabled = ['SYSTEM_TRUSTED_KEYRING', 'KSU', 'KSU_SUSFS', 'KSU_SUSFS_SUS_PATH', 'KSU_SUSFS_SUS_MOUNT',
               'KSU_SUSFS_SUS_KSTAT', 'KSU_SUSFS_SPOOF_UNAME', 'KSU_SUSFS_ENABLE_LOG',
               'KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS', 'KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG',
               'KSU_SUSFS_OPEN_REDIRECT', 'KSU_SUSFS_SUS_MAP']
    for option in enabled:
        subprocess.run(['bash', str(common / 'scripts/config'), '--file', str(config), '-e', option], check=True)
    for option in ['KPM', 'KSU_DEBUG']:
        subprocess.run(['bash', str(common / 'scripts/config'), '--file', str(config), '-d', option], check=True)
    subprocess.run(['bash', str(common / 'scripts/config'), '--file', str(config),
                    '--set-str', 'SYSTEM_TRUSTED_KEYS', 'certs/ace5-stock-module-cert.pem'], check=True)
    # Adding Kconfig symbols changes the canonical defconfig. Disable only its text equality check.
    build_cfg = common / 'build.config.gki'
    write(build_cfg, replace_one(build_cfg.read_text(),
          'POST_DEFCONFIG_CMDS="check_defconfig"', 'POST_DEFCONFIG_CMDS=""'))
    require(not list(common.rglob('*.rej')), 'Rejected patch fragments found')
    subprocess.run(['git', 'apply', '--reverse', '--check', str(patch)], cwd=common, check=True)
    print('Ace 5 SukiSU + SUSFS integration prepared; KPM disabled.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('workspace', type=Path)
    parser.add_argument('addons', type=Path)
    args = parser.parse_args()
    prepare(args.workspace.resolve(), args.addons.resolve())
