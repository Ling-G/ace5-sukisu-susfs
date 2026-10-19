#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import sys

package = Path(__file__).resolve().parents[1]
lock = json.loads((package / 'sources.lock.json').read_text())
addons = Path(sys.argv[1]).resolve()
addons.mkdir(parents=True, exist_ok=True)
repos = {
    'SukiSU': ('https://github.com/SukiSU-Ultra/SukiSU-Ultra.git', 'sukisu'),
    'susfs': ('https://gitlab.com/simonpunk/susfs4ksu.git', 'susfs'),
    'repo': ('https://gerrit.googlesource.com/git-repo', 'repo'),
}
for name, (url, key) in repos.items():
    dest = addons / name
    if dest.exists():
        raise SystemExit('Destination already exists: ' + str(dest))
    subprocess.run(['git', 'init', str(dest)], check=True)
    subprocess.run(['git', '-C', str(dest), 'remote', 'add', 'origin', url], check=True)
    subprocess.run(['git', '-C', str(dest), 'fetch', '--depth=1', 'origin', lock['sources'][key]], check=True)
    subprocess.run(['git', '-C', str(dest), 'checkout', '--detach', 'FETCH_HEAD'], check=True)
    actual = subprocess.check_output(['git', '-C', str(dest), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != lock['sources'][key]:
        raise SystemExit('Commit verification failed: ' + name)
print('Pinned addon sources fetched.')
