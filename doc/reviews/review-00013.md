# PR #13 — Backport workflow review fixes

<!-- gh-id: 4210373720 -->
### copilot-pull-request-reviewer[bot] — COMMENTED ([2026-05-01 07:08 UTC](https://github.com/cmk/template-rust/pull/13#pullrequestreview-4210373720))

## Pull request overview

This PR backports workflow-review fixes and hardens supporting helper scripts so review rounds behave consistently (doc-only rounds use `doc:` commits; code rounds use `fix:`), while improving shell-script safety and workflow-state detection.

**Changes:**
- Make `scripts/workflow_state.sh` resilient to missing `gh` and refine state detection (e.g., `main_unpushed`, `pushed`).
- Improve `scripts/safe_merge.sh` UX and safety (explicit `--help`, allow no-arg invocation, properly shell-quote rerun suggestions).
- Update workflow docs/command docs to reflect `/pull-reviews` implementation and commit-prefix selection for replies-only rounds.

### Reviewed changes

Copilot reviewed 6 out of 6 changed files in this pull request and generated no comments.

<details>
<summary>Show a summary per file</summary>

| File | Description |
| ---- | ----------- |
| scripts/workflow_state.sh | Avoids hard dependency on `gh` and improves FSM state classification for common repo states. |
| scripts/safe_merge.sh | Safer help/no-arg behavior and robust, quoted guidance when refusing to merge due to unpushed commits. |
| scripts/local_review.sh | Extends `--check` to validate additional prerequisites used by the workflow. |
| doc/workflow.md | Clarifies the diagram with the concrete `/pull-reviews` script and `safe_merge.sh` responsibility wording. |
| .claude/commands/watch-pr.md | Ensures commit message prefixes match staged content (doc-only reply rounds vs code edits). |
| .claude/commands/reply-reviews.md | Same staged-content-based commit prefix selection to keep rounds consistent and atomic. |
</details>





