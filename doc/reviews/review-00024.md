# PR #24 - Port workflow review fixes back

## Summary

Port the review-workflow fixes proven in downstream PRs back into the
template:

- Harden workflow guards around PR-number cleanup, dirty merge
  prevention, branch-local review-file state inference, local-review
  commits, and malformed GitHub review API responses.
- Update `/pr-review`, `/pr-reply`, `/pr-watch`, `AGENTS.md`, and
  workflow docs so optional/follow-up/suppressed/low-confidence review
  comments are treated under the Be a Good Gardener rule.
- Add `scripts/check_pii.sh --tree <ref>`, fix multiline layer import
  collection, and tighten audit force-mode behavior.
- Add Python regressions for workflow-state inference, local-review
  commits, PR review JSON shape validation, PII tree scans, allow-list
  filtering, layer import parsing, and audit force mode.

Verification:

- `cargo fmt --all -- --check`
- `bash -n scripts/check_layers.sh scripts/check_pii.sh scripts/git_merge.sh scripts/git_squash.sh scripts/pr_request.sh scripts/pr_review.sh scripts/workflow_state.sh`
- `PYTHONPYCACHEPREFIX=/tmp/template-rust-pycache python3 -m py_compile scripts/audit_run.py scripts/github_client.py scripts/pr_report.py scripts/pr_reply.py tests/test_audit_run.py tests/test_check_layers.py tests/test_check_pii.py tests/test_pr_report.py tests/test_pr_review.py tests/test_workflow_state.py`
- `python3 -m unittest`
- `scripts/check_pii.sh`
- `scripts/check_pii.sh --tree HEAD`
- `scripts/check_layers.sh`
- `scripts/pr_review.sh --check`
- `cargo test --workspace`
- `cargo clippy --all-targets -- -D warnings`

## Local review (2026-05-07)

**Branch:** plan/2026-05-07-03
**Commits:** 3 (origin/main..plan/2026-05-07-03)
**Reviewer:** Codex (`codex review --base origin/main`)

---

The patch adds useful workflow hardening, but the layer checker can now miss forbidden imports when comments contain semicolons, and the new pr-watch recovery marker can fail on a fresh state directory. These should be fixed before considering the patch correct.

Full review comments:

- [P2] Ignore comment semicolons when collecting use groups — scripts/check_layers.sh:86-86
  When a multiline grouped `use` contains a line comment with a semicolon before the forbidden import, this collector stops at the comment line and never inspects the rest of the group. For example, `use crate::{ // ok; ... test, };` in `conn.rs` is then reported as OK even though `conn` still imports the higher `test` layer, so the CI layer gate can be bypassed by harmless prose in comments.

- [P3] Create the pr-watch directory before marker writes — .claude/commands/pr-watch.md:235-236
  On the first productive `/pr-watch` tick, `.pr-watch/` may not exist yet, but this new push-failure recovery path requires writing `.pr-watch/pr-<N>.push-failed-head`. If that marker is not created after a failed push, the next tick hits Step 0d's marker requirement and refuses to retry a commit that was actually produced by `/pr-watch`; add the directory creation to this failure path before writing the marker.
