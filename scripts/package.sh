#!/usr/bin/env bash
# Build the Flow Launcher plugin archive and print its path.
# Usage: scripts/package.sh [out_dir]   (default: dist)
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
out_dir="${1:-$root/dist}"
version="$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["Version"])' "$root/data/plugin.json")"
build_dir="$(mktemp -d)"
trap 'rm -rf "$build_dir"' EXIT

platform="x86_64-pc-windows-msvc"
oldest_python="3.10"
newer_pythons=(3.11 3.12 3.13 3.14)
stage="$build_dir/stage"
site_packages="$stage/plugin/site-packages"

mkdir -p "$stage"
cp -r "$root/src/." "$stage/"
cp "$root/data/icon.png" "$root/data/plugin.json" "$root/data/SettingsTemplate.yaml" "$stage/"
find "$stage" -name __pycache__ -prune -exec rm -rf {} +

vendor() {
  local target="$1" python="$2"
  shift 2
  uv pip install --quiet --target "$target" --python-platform "$platform" --python-version "$python" \
    --only-binary :all: "$@"
}

# streamlink needs lxml, and trio needs cffi on Windows. Neither has a
# pure-Python wheel, so resolve everything for the oldest supported Python,
# then add the compiled modules of each newer Python next to them.
vendor "$site_packages" "$oldest_python" -r "$root/requirements.txt"
rm -rf "$site_packages/bin" "$site_packages/share"

compiled=()
for record in "$site_packages"/*.dist-info/RECORD; do
  if grep -q "\.cp${oldest_python/./}-win_amd64\.pyd," "$record"; then
    dist="$(basename "$(dirname "$record")" .dist-info)"
    compiled+=("${dist%-*}==${dist##*-}")
  fi
done

for python in "${newer_pythons[@]}"; do
  extra="$build_dir/cp${python/./}"
  vendor "$extra" "$python" --no-deps "${compiled[@]}"
  (cd "$extra" && find . -name "*.cp${python/./}-win_amd64.pyd" -exec cp --parents {} "$site_packages/" \;)
done

mkdir -p "$out_dir"
zip_path="$(cd "$out_dir" && pwd)/twitchy-${version}.zip"
rm -f "$zip_path"
(cd "$stage" && zip -qr "$zip_path" .)
echo "$zip_path"
