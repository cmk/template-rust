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

## Local review (2026-05-07)

**Branch:** plan/2026-05-07-03
**Commits:** 4 (origin/main..plan/2026-05-07-03)
**Reviewer:** Codex (`codex review --base origin/main`)

---

The patch leaves two workflow gates with bypasses: layer checking can still miss forbidden imports in valid Rust syntax, and the PII allow-list now suppresses a broad home-path pattern globally. These should be tightened before merging.

Full review comments:

- [P2] Keep block-comment semicolons from ending use groups — scripts/check_layers.sh:87-87
  When a multiline grouped `use` contains a block comment with a semicolon before a higher-layer import, this condition terminates collection before the rest of the group is inspected. For example, `use crate::{ /* ; */ test, };` in `conn.rs` is valid Rust but the layer gate reports OK, so forbidden imports can still bypass CI.

- [P2] Narrow the PII fixture allow-list — .pii-allow:14-14
  Because `.pii-allow` regexes are applied to every offending line, this unanchored entry suppresses any staged or tree hit containing `<home>/project`, including suffixes like `<home>/project/private`, not just the test fixture. That creates a blind spot in the home-path gate; split the fixture string in tests or make the exception specific enough that real matching paths still fail.

## Local review (2026-05-07)

**Branch:** plan/2026-05-07-03
**Commits:** 6 (origin/main..plan/2026-05-07-03)
**Reviewer:** Codex (`codex review --base origin/main`)

---

The new PII tree-scan mode does not preserve the existing allow-list semantics for exact line-content matches, so a documented recovery path for false positives fails.

Review comment:

- [P2] Filter tree-scan allow-lists against line content — scripts/check_pii.sh:116-117
  When `--tree` is used with an anchored `.pii-allow` entry, e.g. `^path=<home>/project$`, this `git grep -n` output is passed through with the `HEAD:file:line:` prefix still attached, so `filter_allowed` no longer matches the documented offending line content. This makes the new tree scan keep failing after users add the suggested exact-line allow-list, and can also let allow-list patterns match file paths rather than the leaked text.


## Local review (2026-05-07)

**Branch:** plan/2026-05-07-03
**Commits:** 8 (origin/main..plan/2026-05-07-03)
**Reviewer:** Codex (`codex review --base origin/main`)

---

The layer-check hardening still has a bypass for multi-line block comments because comment state is not preserved across lines. That can let forbidden imports evade the CI layer gate.

Review comment:

- [P2] Preserve block-comment state across import lines — scripts/check_layers.sh:127-127
  Because `strip_rust_comments_from_line` is invoked through command substitution here, its updates to `in_block_comment` happen in a subshell and are lost before the next input line. When a grouped `use` contains a multi-line block comment with a semicolon before a forbidden layer import, collection stops on the commented semicolon and the later import is never inspected, so `scripts/check_layers.sh` can report OK for a valid Rust import that violates the layer order.

