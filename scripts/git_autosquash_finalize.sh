#!/usr/bin/env bash
# Autosquash transient review fixups before the merge gate.
#
# This is the required pre-merge transition after review rounds have
# pushed `fixup!`, `amend!`, or `squash!` commits. It rewrites the PR
# branch into its reviewable final shape, reruns the same local gates
# that protect pushes, then updates the remote branch with lease.
set -euo pipefail

if [ $# -ne 0 ] || [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  cat >&2 <<'USAGE'
usage: git_autosquash_finalize.sh

Requires a clean worktree on a branch. Fetches origin/main, rebases the
current branch with --autosquash, runs full gates, then force-pushes the
cleaned branch with --force-with-lease.
USAGE
  if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    exit 0
  fi
  exit 2
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "git_autosquash_finalize.sh: not inside a git worktree." >&2
  exit 1
fi
repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

branch=$(git branch --show-current)
if [ -z "$branch" ]; then
  echo "git_autosquash_finalize.sh: detached HEAD; check out the PR branch first." >&2
  exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
  echo "git_autosquash_finalize.sh: working tree is dirty; commit or stash first." >&2
  exit 1
fi

git fetch --quiet origin main
GIT_SEQUENCE_EDITOR=: git rebase -i --autosquash origin/main

cargo fmt --all -- --check
scripts/check_pii.sh
scripts/check_layers.sh
cargo test --workspace
cargo clippy --all-targets -- -D warnings

git push --force-with-lease origin "HEAD:$branch"
