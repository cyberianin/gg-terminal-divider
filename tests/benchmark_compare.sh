#!/usr/bin/env bash
set -eu
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
count=${1:-200}
baseline=$(mktemp -d "$root/tests/.benchmark.XXXXXX")
trap 'rm -rf -- "$baseline"' EXIT
git -C "$root" show HEAD:gg > "$baseline/gg"
cp -- "$root/gg-names.sh" "$baseline/gg-names.sh"
printf 'Baseline (HEAD:gg)\n'
GG_BENCH_ENTRY="$baseline/gg" bash "$root/tests/benchmark.sh" "$count"
printf 'Working tree\n'
GG_BENCH_ENTRY="$root/gg" bash "$root/tests/benchmark.sh" "$count"
