#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
for file in gg gg-names.sh gg-launcher.sh install.sh tests/*.sh; do
    bash -n "$file"
done
shellcheck -x gg gg-names.sh gg-launcher.sh install.sh tests/*.sh
bash tests/test.sh
bash tests/regression.sh
python3 tests/linux_edges.py
