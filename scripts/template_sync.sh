#!/usr/bin/env bash
# template_sync.sh — pull-mode drift check between template-rust and
# downstream repos seeded from it.
#
# template-rust owns a small set of "canonical-shared" files outright:
# workflow scripts, git hooks, the Claude command playbooks, the audit
# docs, the calibration/workflow prose, and the Python regression
# suite. Downstream repos (one per workspace seeded from this one) get
# stale on those files because there's no automated sync. This script
# is the manifest-driven manual sync.
#
# Modes:
#   default          read-only drift report; exits non-zero if any
#                    verbatim path drifted or is missing.
#   --apply          for each downstream, copy every verbatim path
#                    from this working tree into the downstream
#                    working tree. Skips surgical paths and refuses
#                    a dirty downstream tree.
#
# Surgical paths (AGENTS.md, Cargo.toml, rust-toolchain.toml,
# rustfmt.toml, deny.toml, .github/workflows/ci.yml) are reported as
# match-vs-differs only. They encode project-specific facts (MSRV,
# crate names, layer rules, dependency policy) and need a human
# merge — never auto-copied.
#
# Usage:
#   scripts/template_sync.sh <downstream-repo-path>...
#   scripts/template_sync.sh --apply <downstream-repo-path>...
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
usage:
  scripts/template_sync.sh <downstream-repo-path>...
  scripts/template_sync.sh --apply <downstream-repo-path>...

Without --apply, prints a drift report for each downstream repo and
exits 1 if any verbatim path drifted or is missing. With --apply,
copies every verbatim path from this working tree into each downstream
(refuses a dirty downstream tree). Surgical paths are reported but
never copied.
USAGE
}

# --- Manifest ---------------------------------------------------------
#
# Adding a path is a one-line array edit. Keep VERBATIM and SURGICAL
# disjoint; the report has no bucket for "in both."

VERBATIM_PATHS=(
  "scripts/audit_run.py"
  "scripts/audit_report.sh"
  "scripts/check_pii.sh"
  "scripts/check_layers.sh"
  "scripts/git_autosquash_finalize.sh"
  "scripts/git_merge.sh"
  "scripts/git_squash.sh"
  "scripts/github_client.py"
  "scripts/pr_report.py"
  "scripts/pr_request.sh"
  "scripts/pr_reply.py"
  "scripts/pr_review.sh"
  "scripts/template_sync.sh"
  "scripts/workflow_state.sh"
  ".githooks/pre-commit"
  ".githooks/pre-push"
  ".claude/commands/pr-reply.md"
  ".claude/commands/pr-report.md"
  ".claude/commands/pr-review.md"
  ".claude/commands/pr-watch.md"
  "doc/audits/README.md"
  "doc/audits/coverage.md"
  "doc/audits/docrot.md"
  "doc/audits/hygiene.md"
  "doc/audits/pii.md"
  "doc/reviews/calibration.md"
  "doc/workflow.md"
  "tests/__init__.py"
  "tests/test_audit_run.py"
  "tests/test_check_layers.py"
  "tests/test_check_pii.py"
  "tests/test_git_autosquash_finalize.py"
  "tests/test_git_merge.py"
  "tests/test_pr_report.py"
  "tests/test_pr_review.py"
  "tests/test_template_sync.py"
  "tests/test_workflow_state.py"
)

SURGICAL_PATHS=(
  "AGENTS.md"
  "Cargo.toml"
  "rust-toolchain.toml"
  "rustfmt.toml"
  "deny.toml"
  ".github/workflows/ci.yml"
)

# --- Argument parsing -------------------------------------------------

apply=false
declare -a downstream_args
downstream_args=()

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --apply)
      apply=true
      shift
      ;;
    --)
      shift
      while [ $# -gt 0 ]; do
        downstream_args+=("$1")
        shift
      done
      ;;
    -*)
      echo "template_sync.sh: unknown flag: $1" >&2
      usage
      exit 2
      ;;
    *)
      downstream_args+=("$1")
      shift
      ;;
  esac
done

if [ ${#downstream_args[@]} -eq 0 ]; then
  usage
  exit 2
fi

# --- Resolve template-rust root and validate cwd ----------------------

script_dir=$(cd "$(dirname "$0")" && pwd -P)
template_root=$(cd "$script_dir/.." && pwd -P)

# Refuse to run from a worktree that isn't this template repo. The
# script reads template content from `$template_root`; if a stale
# copy of the script lives inside a downstream repo (e.g. delivered
# by a previous --apply) and is invoked from there, the "template"
# side would be whatever stale content lives in that downstream.
#
# Two-step guard: (1) script's parent must be a git toplevel,
# (2) that toplevel must contain the `.template-rust-root` marker.
# The marker is intentionally excluded from VERBATIM_PATHS /
# SURGICAL_PATHS so downstream repos never receive a copy.
if ! template_git_root=$(git -C "$template_root" rev-parse --show-toplevel 2>/dev/null); then
  echo "template_sync.sh: $template_root is not a git working tree." >&2
  exit 2
fi
if [ "$template_git_root" != "$template_root" ]; then
  echo "template_sync.sh: script must run from the template-rust working tree." >&2
  echo "  resolved template root: $template_root" >&2
  echo "  git toplevel:           $template_git_root" >&2
  exit 2
fi
if [ ! -f "$template_root/.template-rust-root" ]; then
  echo "template_sync.sh: $template_root is missing the .template-rust-root marker." >&2
  echo "  this script must run from the canonical template-rust repo, not a stale downstream copy." >&2
  exit 2
fi

# --- Validate downstream args -----------------------------------------

declare -a downstream_roots
downstream_roots=()

for raw in "${downstream_args[@]}"; do
  if [ ! -d "$raw" ]; then
    echo "template_sync.sh: downstream path is not a directory: $raw" >&2
    exit 2
  fi
  if ! abs=$(cd "$raw" && pwd -P); then
    echo "template_sync.sh: cannot enter downstream path: $raw" >&2
    exit 2
  fi
  if ! down_git_root=$(git -C "$abs" rev-parse --show-toplevel 2>/dev/null); then
    echo "template_sync.sh: downstream path is not a git working tree: $raw" >&2
    exit 2
  fi
  if [ "$down_git_root" = "$template_root" ]; then
    echo "template_sync.sh: refusing to sync template-rust to itself: $raw" >&2
    exit 2
  fi
  if [ ${#downstream_roots[@]} -gt 0 ]; then
    for prev in "${downstream_roots[@]}"; do
      if [ "$prev" = "$down_git_root" ]; then
        echo "template_sync.sh: downstream path passed twice: $raw" >&2
        exit 2
      fi
    done
  fi
  downstream_roots+=("$down_git_root")
done

# --- Per-downstream processing ----------------------------------------

overall_drift=0

report_one() {
  local downstream="$1"
  local heading="=== $downstream ==="
  printf '%s\n' "$heading"

  if [ "$apply" = true ]; then
    if [ -n "$(git -C "$downstream" status --porcelain)" ]; then
      echo "template_sync.sh: refusing --apply on dirty downstream: $downstream" >&2
      echo "  commit or stash local changes first." >&2
      exit 2
    fi
  fi

  local drift_count=0
  local missing_count=0
  local applied_count=0
  local match_count=0
  local surgical_match=0
  local surgical_diff=0
  local rel src dst

  for rel in "${VERBATIM_PATHS[@]}"; do
    src="$template_root/$rel"
    dst="$downstream/$rel"
    if [ ! -e "$src" ]; then
      echo "template_sync.sh: manifest entry missing in template: $rel" >&2
      echo "  the manifest and template must stay in sync; aborting." >&2
      exit 2
    fi
    if [ ! -e "$dst" ]; then
      printf '  %s: missing downstream\n' "$rel"
      missing_count=$((missing_count + 1))
      if [ "$apply" = true ]; then
        mkdir -p "$(dirname "$dst")"
        install -m "$(stat -c '%a' "$src" 2>/dev/null || stat -f '%Lp' "$src")" "$src" "$dst"
        applied_count=$((applied_count + 1))
      fi
      continue
    fi
    if cmp -s "$src" "$dst"; then
      match_count=$((match_count + 1))
      continue
    fi
    printf '  %s: drift\n' "$rel"
    diff -u --label "template/$rel" --label "downstream/$rel" \
      "$src" "$dst" | sed -n '1,40p' || true
    drift_count=$((drift_count + 1))
    if [ "$apply" = true ]; then
      install -m "$(stat -c '%a' "$src" 2>/dev/null || stat -f '%Lp' "$src")" "$src" "$dst"
      applied_count=$((applied_count + 1))
    fi
  done

  for rel in "${SURGICAL_PATHS[@]}"; do
    src="$template_root/$rel"
    dst="$downstream/$rel"
    if [ ! -e "$src" ]; then
      echo "template_sync.sh: manifest entry missing in template: $rel" >&2
      echo "  the manifest and template must stay in sync; aborting." >&2
      exit 2
    fi
    if [ ! -e "$dst" ]; then
      printf '  %s: missing downstream (surgical — not auto-copied)\n' "$rel"
      surgical_diff=$((surgical_diff + 1))
      continue
    fi
    if cmp -s "$src" "$dst"; then
      surgical_match=$((surgical_match + 1))
      continue
    fi
    printf '  %s: differs (surgical merge required)\n' "$rel"
    surgical_diff=$((surgical_diff + 1))
  done

  printf '  summary: verbatim match=%d drift=%d missing=%d' \
    "$match_count" "$drift_count" "$missing_count"
  if [ "$apply" = true ]; then
    printf ' applied=%d' "$applied_count"
  fi
  printf '  surgical match=%d differs=%d\n' "$surgical_match" "$surgical_diff"

  if [ "$drift_count" -gt 0 ] || [ "$missing_count" -gt 0 ]; then
    overall_drift=1
  fi
}

for downstream in "${downstream_roots[@]}"; do
  report_one "$downstream"
done

if [ "$apply" = true ]; then
  cat <<'NEXT'

template_sync.sh: --apply done.
Surgical paths were reported but never copied; merge them by hand
where the report says "differs (surgical merge required)".
Review each downstream with `git -C <path> status` / `git diff` and
land via the normal plan/YYYY-MM-DD-NN branch.
NEXT
  exit 0
fi

exit "$overall_drift"
