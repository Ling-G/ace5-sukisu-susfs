#!/usr/bin/env bash
set -euo pipefail
PACKAGE=$(cd "$(dirname "$0")/.." && pwd)
WORKSPACE=$1
ADDONS=$2
MANIFEST=$3
mkdir -p "$MANIFEST" "$WORKSPACE"
cp "$PACKAGE/manifests/ace5.xml" "$MANIFEST/ace5.xml"
git -C "$MANIFEST" init
git -C "$MANIFEST" add ace5.xml
git -C "$MANIFEST" -c user.name=Ace5Build -c user.email=build@localhost commit --no-gpg-sign -m "Pinned Ace 5 manifest"
REPO_REV=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sources"]["repo"])' "$PACKAGE/sources.lock.json")
cd "$WORKSPACE"
python3 "$ADDONS/repo/repo" init -u "$MANIFEST" -m ace5.xml --depth=1 --repo-url=https://gerrit.googlesource.com/git-repo --repo-rev="$REPO_REV"
python3 "$ADDONS/repo/repo" sync -c --no-tags --no-clone-bundle -j4 --fail-fast
python3 "$ADDONS/repo/repo" manifest -r -o "$PACKAGE/output/resolved-manifest.xml"
