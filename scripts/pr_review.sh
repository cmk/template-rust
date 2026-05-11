#!/usr/bin/env bash
# Codex implementation of the plan_finalized -> local_reviewed FSM transition.
set -euo pipefail

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(git -C "$script_dir/.." rev-parse --show-toplevel)
cd "$repo_root"

if [ "${1:-}" = "--check" ]; then
  command -v codex >/dev/null
  codex review --help >/dev/null
  command -v gh >/dev/null
  scripts/pr_report.py path 1 >/dev/null
  scripts/workflow_state.sh
  exit 0
fi

if ! command -v codex >/dev/null; then
  echo "error: codex CLI not found on PATH" >&2
  exit 1
fi

if ! command -v gh >/dev/null; then
  echo "error: gh CLI not found on PATH" >&2
  exit 1
fi

git fetch --quiet origin main

if [ -n "$(git status --porcelain)" ]; then
  echo "error: working tree must be clean before local review" >&2
  exit 1
fi

if git diff --quiet origin/main...HEAD; then
  echo "error: nothing to review against origin/main" >&2
  exit 1
fi

review_file=''
branch_review_files=()
while IFS= read -r path; do
  case "$path" in
    doc/reviews/review-00000.md) ;;
    doc/reviews/review-[0-9][0-9][0-9][0-9][0-9].md)
      branch_review_files+=("$path")
      ;;
  esac
done < <(git diff --name-only --diff-filter=ACMR origin/main...HEAD -- 'doc/reviews/review-*.md' 2>/dev/null || true)

if [ "${#branch_review_files[@]}" -eq 1 ]; then
  review_file="${branch_review_files[0]}"
elif [ "${#branch_review_files[@]}" -gt 1 ]; then
  echo "error: multiple branch review files found:" >&2
  printf '  %s\n' "${branch_review_files[@]}" >&2
  exit 1
elif ! review_file=$(scripts/pr_report.py path); then
  echo "error: could not determine review file path" >&2
  echo "  ensure gh is authenticated, or run scripts/pr_request.sh owner/name to diagnose GitHub access." >&2
  exit 1
fi
if [ ! -f "$review_file" ]; then
  echo "error: review file not found: $review_file" >&2
  echo "  run TDD step 7 first: finalize the plan and draft PR description." >&2
  exit 1
fi

if ! grep -q '^## Summary[[:space:]]*$' "$review_file"; then
  echo "error: review file is missing ## Summary: $review_file" >&2
  exit 1
fi

branch=$(git branch --show-current)
commits=$(git rev-list --count origin/main..HEAD)
date=$(date +%F)

tmp=$(mktemp)
sanitized_tmp=$(mktemp)
trap 'rm -f "$tmp" "$sanitized_tmp"' EXIT

# Record which prompt files codex sees, *before* invoking it, so the
# fingerprint is guaranteed to match the version codex loads. (If we
# computed after the run, a concurrent edit between codex's read and
# our hash would silently desync.) This is the version codex saw.
agents_sha=$(git hash-object AGENTS.md 2>/dev/null || echo missing)
if [ -f doc/reviews/calibration.md ]; then
  calib_sha=$(git hash-object doc/reviews/calibration.md)
else
  calib_sha=missing
fi

# Codex CLI 0.125 rejects a custom prompt together with --base, even
# though help advertises both. AGENTS.md is discovered from the repo
# root, so use the supported base-review invocation.
codex review --base origin/main >"$tmp"
python3 - "$repo_root" "$tmp" "$sanitized_tmp" <<'PY'
import re
from pathlib import Path
import sys

repo_root, src, dst = sys.argv[1:]
text = Path(src).read_text(encoding="utf-8")
text = text.replace(repo_root + "/", "")
text = text.replace(repo_root, ".")
text = re.sub(r"/Users/[A-Za-z0-9._-]+/", "<home>/", text)
text = re.sub(r"/home/[A-Za-z0-9._-]+/", "<home>/", text)
Path(dst).write_text(text, encoding="utf-8")
PY

{
  printf '\n## Local review (%s)\n\n' "$date"
  printf '**Branch:** %s\n' "$branch"
  printf '**Commits:** %s (origin/main..%s)\n' "$commits" "$branch"
  printf '**Reviewer:** Codex (`codex review --base origin/main`)\n'
  printf '**Prompt fingerprint:** AGENTS.md=%s calibration=%s\n\n' \
    "$agents_sha" "$calib_sha"
  printf '%s\n\n' '---'
  cat "$sanitized_tmp"
  printf '\n'
} >>"$review_file"

git add -- "$review_file"
if git diff --cached --quiet; then
  printf 'local review appended with no staged delta: %s\n' "$review_file"
else
  if ! doc_commit=$(git log -n 1 --follow --diff-filter=A --format=%H -- "$review_file"); then
    echo "error: could not find finalized-doc commit for $review_file" >&2
    exit 1
  fi
  if [ -z "$doc_commit" ]; then
    echo "error: could not find finalized-doc commit for $review_file" >&2
    exit 1
  fi
  git commit --fixup="$doc_commit"
  printf 'local review committed: %s\n' "$review_file"
fi
