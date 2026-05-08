# PR #25 - Delegate pr-review Path Selection

## Summary

This PR fixes the Claude Code `/pr-review` command wrapper so it no longer aborts before `scripts/pr_review.sh` can apply its branch-local review-file fallback.

The shell script already handles PR-number drift by scanning `git diff origin/main...HEAD` for exactly one committed `doc/reviews/review-NNNNN.md` before falling back to the newly predicted path. The command file still told Claude to predict the path itself and abort if that file was missing, which masked the script fallback.

Changes:

- Remove the duplicated predicted-path existence gate from `.claude/commands/pr-review.md`.
- Document that review-file selection and `## Summary` validation belong to `scripts/pr_review.sh`.
- Tell the command to use the path printed by the script when reading back the appended local-review section.

Verification:

- `bash -n scripts/pr_review.sh`
- `python3 -B -m unittest tests.test_pr_review`
- `rg` check confirmed the old abort wording is gone and the branch-local fallback wording is present.
- `scripts/pr_review.sh --check`
- `git diff --check`
- `cargo test --workspace`
- `cargo clippy --all-targets -- -D warnings`
