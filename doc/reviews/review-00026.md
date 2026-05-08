# PR #26 - Batch Tree PII Scans

## Summary

This PR fixes `scripts/check_pii.sh --tree` so committed-tree scans run one `git grep` across the tree instead of spawning `git grep` once per tracked file.

The CLI and report format stay the same. The scanner still excludes `scripts/check_pii.sh` and `.pii-allow`, and `.pii-allow` still filters matched content rather than file locations.

Changes:

- Replace the per-file `git ls-tree` / `git grep` loop with one NUL-delimited tree-wide `git grep`.
- Preserve the existing `tree:path:line:content` report shape.
- Add a regression that wraps `git` and asserts tree mode invokes `git grep` once while reporting multiple leaking files.

Verification:

- `bash -n scripts/check_pii.sh`
- `python3 -B -m unittest tests.test_check_pii`
- `python3 -B -m unittest`
- `scripts/check_pii.sh --tree HEAD`
- `git diff --check`
- `cargo test --workspace`
- `cargo clippy --all-targets -- -D warnings`

<!-- gh-id: 4250890859 -->
### copilot-pull-request-reviewer[bot] — COMMENTED ([2026-05-08 08:50 UTC](https://github.com/cmk/template-rust/pull/26#pullrequestreview-4250890859))

## Pull request overview

This pull request improves the performance of committed-tree PII scanning by changing `scripts/check_pii.sh --tree` from a per-file `git grep` loop to a single tree-wide `git grep` invocation, while keeping the CLI and report format stable.

**Changes:**
- Batch `--tree` scanning into one NUL-delimited `git grep` over the whole tree (with excludes preserved).
- Preserve the existing `tree_ref:path:line:content` report output shape and allowlist semantics.
- Add a Python regression test intended to assert `--tree` mode invokes `git grep` once while still reporting multiple leaking files.

### Reviewed changes

Copilot reviewed 4 out of 4 changed files in this pull request and generated 1 comment.

| File | Description |
| ---- | ----------- |
| scripts/check_pii.sh | Replace per-file tree scanning with a single tree-wide `git grep -z` and post-process matches. |
| tests/test_check_pii.py | Add a regression test that wraps `git` to count `git grep` invocations in `--tree` mode. |
| doc/plans/plan-2026-05-08-02.md | Document the plan/verification steps for batching tree scans and process-count testing. |
| doc/reviews/review-00026.md | Add the PR review audit entry (not reviewed for findings per repo guidelines). |





<!-- gh-id: 3207518055 -->
### Copilot on [`tests/test_check_pii.py:203`](https://github.com/cmk/template-rust/pull/26#discussion_r3207518055) (2026-05-08 08:50 UTC)

The new regression test only checks that both filenames appear somewhere in stderr; it doesn’t assert that tree-mode produced two distinct `tree_ref:path:line:content` entries. A parsing bug in the NUL-delimited `git grep` output could concatenate records and still contain both filenames, letting the test pass while the report shape is wrong. Consider asserting that stderr contains separate lines matching `HEAD:leak_one.txt:` and `HEAD:leak_two.txt:` (and ideally their respective line numbers/content) to validate the multi-match parsing behavior in addition to the process-count behavior.


<!-- gh-id: 3207533691 -->
#### ↳ cmk ([2026-05-08 08:53 UTC](https://github.com/cmk/template-rust/pull/26#discussion_r3207533691))

Fixed - the regression now asserts separate HEAD:leak_one.txt:1:path=... and HEAD:leak_two.txt:1:path=... report entries, so it verifies multi-match parsing as well as the one-grep process count.
