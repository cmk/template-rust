# PR #12 — Canonicalize agent workflow instructions

<!-- gh-id: 4209379019 -->
### copilot-pull-request-reviewer[bot] — COMMENTED ([2026-05-01 00:48 UTC](https://github.com/cmk/template-rust/pull/12#pullrequestreview-4209379019))

## Pull request overview

This PR standardizes the repository’s agent workflow documentation by making `AGENTS.md` the canonical instruction source (with `CLAUDE.md` kept for compatibility), and adds/updates workflow tooling and docs to support local-review and FSM state reporting paths.

**Changes:**
- Introduces `AGENTS.md` as the shared agent instruction file and updates docs/commands to reference it instead of `CLAUDE.md`.
- Adds `scripts/local_review.sh` (Codex-driven local-review transition) and `scripts/workflow_state.sh` (read-only FSM state reporter).
- Updates workflow diagrams and README narrative to reflect the local-review and review-round FSM transitions.

### Reviewed changes

Copilot reviewed 11 out of 12 changed files in this pull request and generated 3 comments.

<details>
<summary>Show a summary per file</summary>

| File | Description |
| ---- | ----------- |
| scripts/workflow_state.sh | New script to infer/report current workflow FSM state from git/gh + review doc signals. |
| scripts/next_pr_number.sh | Updates comments to reflect use by the local review transition. |
| scripts/local_review.sh | New Codex-based `plan_finalized → local_reviewed` transition script that appends a local review section into the review doc. |
| scripts/extract_pr_body.sh | Updates reference from `CLAUDE.md` to `AGENTS.md` as the workflow authority. |
| doc/workflow.md | Updates authoritative reference to `AGENTS.md` and documents `scripts/local_review.sh` as an alternative local-review transition. |
| doc/reviews/review-00000.md | Updates guidance text to match the new local review transition wording. |
| README.md | Updates top-level pointers to `AGENTS.md` and refreshes workflow/review loop descriptions. |
| AGENTS.md | New canonical agent workflow/spec document consolidating repo conventions, FSM workflow, and review processes. |
| .claude/commands/watch-pr.md | Updates conventions reference from `CLAUDE.md` to `AGENTS.md`. |
| .claude/commands/sprint-review.md | Reframes `/sprint-review` as the Claude implementation of the FSM transition and updates references to `AGENTS.md`. |
</details>






<!-- gh-id: 3171581512 -->
### Copilot on [`scripts/local_review.sh:80`](https://github.com/cmk/template-rust/pull/12#discussion_r3171581512) (2026-05-01 00:48 UTC)

This script reads/writes paths like `doc/plans/...`, `doc/reviews/...`, and `AGENTS.md` using relative paths, so it effectively requires being run from the repo root. If invoked from another directory, `review_path.sh` will emit a relative path and the subsequent `-f` check / append will target the wrong location or fail. Recommend `cd "$(git rev-parse --show-toplevel)"` early (or derive repo root from `script_dir`) to make behavior location-independent.

<!-- gh-id: 3171581537 -->
### Copilot on [`AGENTS.md`](https://github.com/cmk/template-rust/pull/12#discussion_r3171581537) (2026-05-01 00:48 UTC)

The note that `cargo fmt --check` was made blocking "after a real CI fmt failure" looks inconsistent with the current CI config, which runs `cargo fmt --check` with `continue-on-error: true` (warn-only) in `.github/workflows/ci.yml`. Either update the wording here to reflect that fmt drift is caught locally (not by CI), or change CI to fail on fmt if that’s the intended guarantee.


<!-- gh-id: 3171581544 -->
### Copilot on [`scripts/workflow_state.sh:45`](https://github.com/cmk/template-rust/pull/12#discussion_r3171581544) (2026-05-01 00:48 UTC)

`review_file` resolution assumes the script is run from the repo root (it calls `scripts/review_path.sh` and then checks `-f` on a relative path). If `scripts/workflow_state.sh` is invoked from a subdirectory, this will mis-detect the review file as missing and can yield an incorrect FSM state. Consider resolving the repo root via `git rev-parse --show-toplevel` (or `script_dir` → repo root) and `cd` there before computing `review_file`, or make all referenced paths absolute.
