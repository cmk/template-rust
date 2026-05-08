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
