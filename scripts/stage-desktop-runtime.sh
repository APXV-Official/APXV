#!/usr/bin/env bash
# Stage runtime payload for Tauri bundle (no operator managed/ or keys/).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEV_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUNTIME_ROOT="$DEV_ROOT/runtime"
if [[ ! -f "$RUNTIME_ROOT/pyproject.toml" ]]; then
  RUNTIME_ROOT="$DEV_ROOT"
fi
PAYLOAD_ROOT="$DEV_ROOT/ui/apps/desktop/runtime-payload"

INCLUDE_DIRS=(agents governance-libraries scripts rust examples docs)
INCLUDE_FILES=(pyproject.toml requirements.txt requirements-dev.txt README.md)

if [[ -d "$PAYLOAD_ROOT" ]]; then
  chmod -R u+w "$PAYLOAD_ROOT" 2>/dev/null || true
  rm -rf "$PAYLOAD_ROOT"
fi
mkdir -p "$PAYLOAD_ROOT"

copy_tree() {
  local src="$1"
  local dst="$2"
  if [[ ! -d "$src" ]]; then
    return 0
  fi
  cp -a "$src" "$dst"
}

strip_keys_dirs() {
  local root="$1"
  find "$root" -type d -name keys | while read -r keys_dir; do
    find "$keys_dir" -maxdepth 1 -type f -delete 2>/dev/null || true
  done
}

filter_release_binaries() {
  local release_dir="$1"
  if [[ ! -d "$release_dir" ]]; then
    return 0
  fi
  case "$(uname -s)" in
    Darwin|Linux)
      find "$release_dir" -maxdepth 1 -type f -name '*.exe' -delete 2>/dev/null || true
      ;;
    MINGW*|MSYS*|CYGWIN*|Windows_NT)
      find "$release_dir" -maxdepth 1 -type f ! -name '*.exe' \
        \( -name 'apxv-zk' -o -name 'apxv-circuits' -o -name 'apx-zk' -o -name 'apx-circuits' \) \
        -delete 2>/dev/null || true
      ;;
  esac
}

prune_operator_docs() {
  local docs_root="$1"
  rm -rf "$docs_root/internal" "$docs_root/resume" 2>/dev/null || true
}

seed_managed_governance_specs() {
  # Baseline rule/workflow/knowledge files required for bootstrap_active_specs_if_needed.
  local specs=(rules/rule1.md workflows/workflow1.md knowledge/knowledge1.md)
  for spec in "${specs[@]}"; do
    local src="$RUNTIME_ROOT/managed/$spec"
    local dst="$PAYLOAD_ROOT/managed/$spec"
    if [[ -f "$src" ]]; then
      mkdir -p "$(dirname "$dst")"
      cp -f "$src" "$dst"
    fi
  done
}

for dir in "${INCLUDE_DIRS[@]}"; do
  src="$RUNTIME_ROOT/$dir"
  dst="$PAYLOAD_ROOT/$dir"
  copy_tree "$src" "$dst"
  if [[ "$dir" == "docs" && -d "$dst" ]]; then
    prune_operator_docs "$dst"
  fi
  if [[ "$dir" == "rust" && -d "$dst" ]]; then
    strip_keys_dirs "$dst"
    rm -rf "$dst/target/debug" 2>/dev/null || true
    case "$(uname -s)" in
      Darwin|Linux)
        find "$dst/target" -type f \( -name '*.exe' -o -name '*.pdb' \) -delete 2>/dev/null || true
        ;;
    esac
    filter_release_binaries "$dst/target/release"
  fi
done

for file in "${INCLUDE_FILES[@]}"; do
  src="$RUNTIME_ROOT/$file"
  if [[ -f "$src" ]]; then
    cp -f "$src" "$PAYLOAD_ROOT/$file"
  fi
done

seed_managed_governance_specs

echo "Staged desktop runtime payload -> $PAYLOAD_ROOT"