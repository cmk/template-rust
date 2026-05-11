# PR #21 — Detect pushed workflow-state branches

<!-- gh-id: 3199858762 -->
### Copilot on [`tests/test_workflow_state.py:22`](https://github.com/cmk/template-rust/pull/21#discussion_r3199858762) (2026-05-07 08:05 UTC)

`run_state()` inherits the caller environment (`os.environ.copy()`), which can make the test non-hermetic. In particular, if `WORKFLOW_REVIEW_FILE` is set in the developer/CI environment, `workflow_state.sh` will report a non-`unknown` `review_file` and the assertions will fail. Consider explicitly unsetting `WORKFLOW_REVIEW_FILE` (and any other workflow-state env knobs you rely on) in `env` for this test run.


<!-- gh-id: 3199858812 -->
### Copilot on [`tests/test_workflow_state.py:28`](https://github.com/cmk/template-rust/pull/21#discussion_r3199858812) (2026-05-07 08:05 UTC)

`env["PATH"]` is hardcoded to `/bin:/usr/bin` to hide `gh`, but this can also hide `git`, `bash`, or `env` on systems where they live elsewhere (e.g., Nix/Homebrew), causing a false-negative test failure. A more robust approach is to construct PATH from the actual locations of required executables (e.g., via `shutil.which("git")`/`shutil.which("bash")`) while ensuring `gh` is not present, or to prepend a temp dir that shadows `gh` and keep the rest of PATH intact.

<!-- gh-id: 4242185018 -->
### copilot-pull-request-reviewer[bot] — COMMENTED ([2026-05-07 08:05 UTC](https://github.com/cmk/template-rust/pull/21#pullrequestreview-4242185018))

## Pull request overview

Updates the workflow state probe to correctly classify clean, pushed feature branches as `pushed` even when GitHub PR lookup (`gh pr view`) and/or local review files are unavailable, with a new regression test and accompanying plan/review docs.

**Changes:**
- Adjusts `scripts/workflow_state.sh` to infer `pushed` purely from git topology (ahead/behind vs `origin/<branch>` plus commits over `origin/main`), while still prioritizing `gh_review` when a PR number is detected.
- Refactors review-file path selection so the opt-in fallback only runs when no explicit review file path is known.
- Adds a Python regression test that builds a temporary repo+bare remote and verifies the `pushed` classification when no review file is present.

### Reviewed changes

Copilot reviewed 4 out of 4 changed files in this pull request and generated 3 comments.

| File | Description |
| ---- | ----------- |
| scripts/workflow_state.sh | Updates state classification and review-file fallback behavior to detect pushed branches without relying on `gh`/review artifacts. |
| tests/test_workflow_state.py | Adds a regression test covering the “clean branch pushed to origin but no PR/review file” scenario. |
| doc/reviews/review-00021.md | Adds the PR-local review record for this change. |
| doc/plans/plan-2026-05-07-01.md | Adds the implementation/verification plan for the workflow-state fix. |





<!-- gh-id: 3199858856 -->
### Copilot on [`tests/test_workflow_state.py:40`](https://github.com/cmk/template-rust/pull/21#discussion_r3199858856) (2026-05-07 08:05 UTC)

This regression test won’t run in the current GitHub Actions CI configuration (the existing `.github/workflows/ci.yml` only runs `cargo` checks). If the intent is to prevent regressions automatically, consider adding a CI step to run `python3 -m unittest` so this test executes on PRs.

<!-- gh-id: 3199921282 -->
#### ↳ cmk ([2026-05-07 08:16 UTC](https://github.com/cmk/template-rust/pull/21#discussion_r3199921282))

Fixed in `6d33922`: `run_state()` now explicitly removes `WORKFLOW_REVIEW_FILE` and `WORKFLOW_STATE_ALLOW_REVIEW_PATH_FALLBACK` before invoking `workflow_state.sh`. The test also sets those variables with `mock.patch.dict()` before calling `run_state()` so this stays covered.

<!-- gh-id: 3199923760 -->
#### ↳ cmk ([2026-05-07 08:16 UTC](https://github.com/cmk/template-rust/pull/21#discussion_r3199923760))

Fixed in `6d33922`: the test no longer hardcodes `PATH` to `/bin:/usr/bin`. It prepends a temp directory containing a failing `gh` shim to the existing `PATH`, so normal tools such as `git`, `bash`, and `env` still resolve from the host environment while `gh pr view` remains unavailable for the regression.

<!-- gh-id: 3199924811 -->
#### ↳ cmk ([2026-05-07 08:16 UTC](https://github.com/cmk/template-rust/pull/21#discussion_r3199924811))

Fixed in `6d33922`: `.github/workflows/ci.yml` now runs `python3 -m unittest`, so the workflow-state regression test is exercised in CI instead of only locally.
