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
