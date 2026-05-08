#!/usr/bin/env bash
# Fail the commit if the staged diff introduces PII or likely secrets.
#
# Scans only lines the commit ADDS (drops unchanged context, deletions,
# and pre-existing content). Checks for:
#   - Absolute user-home paths: /Users/<name>/ (macOS), /home/<name>/
#     (Linux) — catches any committer, including CI runner paths
#   - Private-key headers: -----BEGIN ... PRIVATE KEY-----
#   - Cloud/API token shapes: AWS AKIA, GitHub ghp_, Anthropic/OpenAI sk-
#
# Allow-list exceptions live in `.pii-allow` (one extended regex per
# line; blank lines and `#`-comments ignored). A hit is dropped if the
# offending line matches any allow-list pattern, so exceptions stay
# explicit and reviewable. `/home/runner/` paths in CI docs are a
# typical allow-list candidate.
#
# Default runtime is O(diff), not O(repo). `--tree <ref>` scans a committed
# tree when checking history or CI state after a bypassed hook.
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
usage:
  scripts/check_pii.sh
  scripts/check_pii.sh --tree <rev-or-ref>

Without arguments, scan added lines in the staged diff. With --tree,
scan tracked file content in the named committed tree.
USAGE
}

mode=staged
tree_ref=''
if [ $# -gt 0 ]; then
  case "${1:-}" in
    --tree)
      if [ $# -ne 2 ]; then
        usage
        exit 2
      fi
      mode=tree
      tree_ref="$2"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
fi

patterns=(
  '/Users/[a-zA-Z0-9._-]+/'
  '/home/[a-zA-Z0-9._-]+/'
  '-----BEGIN [A-Z ]*PRIVATE KEY-----'
  'AKIA[0-9A-Z]{16}'
  'ghp_[A-Za-z0-9]{36}'
  'sk-[A-Za-z0-9]{20,}'
)
alt=$(IFS='|'; echo "${patterns[*]}")
allow_patterns=''

load_worktree_allow_patterns() {
  if [ -f .pii-allow ]; then
    allow_patterns=$(grep -vE '^[[:space:]]*(#|$)' .pii-allow || true)
  fi
}

load_tree_allow_patterns() {
  local raw=''
  if raw=$(git show "$tree_ref:.pii-allow" 2>/dev/null); then
    allow_patterns=$(printf '%s\n' "$raw" | grep -vE '^[[:space:]]*(#|$)' || true)
  fi
}

filter_allowed() {
  local input="$1"
  [ -z "$input" ] && return 0

  if [ -n "$allow_patterns" ]; then
    input=$(printf '%s\n' "$input" \
      | grep -vE -f <(printf '%s\n' "$allow_patterns") || true)
  fi

  if [ -n "$input" ]; then
    printf '%s\n' "$input"
  fi
  return 0
}

report=''

if [ "$mode" = staged ]; then
  load_worktree_allow_patterns
  # ACMR = Added / Copied / Modified / Renamed; excludes pure deletions.
  # The script and the allow-list itself are skipped so self-inclusion
  # of the patterns doesn't trip the check.
  #
  # Read names via NUL terminators so paths with spaces/newlines survive.
  while IFS= read -r -d '' f; do
    [ -z "$f" ] && continue
    added=$(git diff --cached -U0 --no-color -- "$f" \
      | grep -E '^\+[^+]' | sed 's/^+//' || true)
    [ -z "$added" ] && continue

    matches=$(printf '%s\n' "$added" | grep -E "$alt" || true)
    matches=$(filter_allowed "$matches")
    [ -z "$matches" ] && continue

    report+="  $f:"$'\n'
    while IFS= read -r line; do
      report+="    $line"$'\n'
    done <<< "$matches"
  done < <(
    git diff --cached --name-only -z --diff-filter=ACMR -- \
      . ':(exclude)scripts/check_pii.sh' ':(exclude).pii-allow'
  )
else
  if ! git rev-parse --verify --quiet "${tree_ref}^{tree}" >/dev/null; then
    echo "error: not a valid tree-ish: $tree_ref" >&2
    exit 2
  fi
  load_tree_allow_patterns

  tree_report=''
  tree_matches=$(mktemp)
  tree_errors=$(mktemp)
  trap 'rm -f "$tree_matches" "$tree_errors"' EXIT

  set +e
  git grep -z -I -n --no-color -E "$alt" "$tree_ref" -- \
    . ':(exclude)scripts/check_pii.sh' ':(exclude).pii-allow' \
    >"$tree_matches" 2>"$tree_errors"
  status=$?
  set -e
  if [ "$status" -eq 1 ]; then
    :
  elif [ "$status" -ne 0 ]; then
    echo "error: git grep failed while scanning tree $tree_ref:" >&2
    cat "$tree_errors" >&2
    exit 2
  else
    while IFS= read -r -d '' location \
      && IFS= read -r -d '' line_no \
      && IFS= read -r content; do
      path="${location#"$tree_ref:"}"
      [ -z "$(filter_allowed "$content")" ] && continue
      tree_report+="    $tree_ref:$path:$line_no:$content"$'\n'
    done < "$tree_matches"
  fi

  if [ -n "$tree_report" ]; then
    report+="  $tree_ref:"$'\n'
    report+="$tree_report"
  fi
fi

if [ -z "$report" ]; then
  exit 0
fi

{
  if [ "$mode" = staged ]; then
    echo "error: staged diff contains potential PII or secrets:"
  else
    echo "error: tree $tree_ref contains potential PII or secrets:"
  fi
  printf '%s' "$report"
  if [ "$mode" = staged ]; then
    echo "  If these are false positives, add a regex to .pii-allow and re-stage."
  else
    echo "  If these are false positives, add a regex to .pii-allow and re-run."
  fi
} >&2
exit 1
