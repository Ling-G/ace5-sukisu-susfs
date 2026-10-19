#!/usr/bin/env bash
set -euo pipefail
PACKAGE=$(cd "$(dirname "$0")/.." && pwd)
WORKSPACE=$1
ADDONS=$2
mkdir -p "$PACKAGE/output" "$PACKAGE/logs"
python3 "$PACKAGE/scripts/prepare.py" "$WORKSPACE" "$ADDONS" 2>&1 | tee "$PACKAGE/logs/integration.log"
cd "$WORKSPACE"
python3 kernel_platform/build_with_bazel.py -t pineapple gki 2>&1 | tee "$PACKAGE/logs/build.log"
python3 "$PACKAGE/scripts/collect.py" "$WORKSPACE" "$PACKAGE/output"
