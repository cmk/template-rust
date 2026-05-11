# PR #14 — Patch workflow FSM follow-ups

<!-- gh-id: 3172519595 -->
### Copilot on [`scripts/safe_merge.sh:65`](https://github.com/cmk/template-rust/pull/14#discussion_r3172519595) (2026-05-01 07:52 UTC)

The new “selector must come before flags” scan treats any non-dash argument after a leading flag as an invalid PR selector. That breaks valid `gh pr merge` invocations where a flag takes a value (e.g., `--repo owner/name`, `--body-file path`, etc.), because those values don’t start with `-` and will trigger this error.

Consider parsing only a single explicit selector (first non-flag arg) and otherwise allowing non-flag values that belong to known flags, or switching to an approach that doesn’t need to interpret `gh`’s flag/value structure (e.g., require selector as arg1 if present, but don’t reject other non-flag tokens when arg1 is a flag).
```suggestion
# forwarded merge command checking the same PR without trying to parse
# `gh`'s full flag/value grammar, only treat argv[1] as an explicit PR
# selector when it is non-flag; otherwise let `gh` interpret the rest.
```

<!-- gh-id: 3172519610 -->
### Copilot on [`scripts/local_review.sh:61`](https://github.com/cmk/template-rust/pull/14#discussion_r3172519610) (2026-05-01 07:52 UTC)

After switching to `codex review --base origin/main` without piping a custom prompt, `plan_context` / `calibration_context` (and the reads of `doc/plans/*` / `doc/reviews/review-calibration.md`) no longer affect the Codex invocation. This leaves dead code and extra filesystem work in the hot path.

Either remove those context-building blocks, or re-introduce them via a supported Codex mechanism (if available) so they’re actually used.

<!-- gh-id: 3172519616 -->
### Copilot on [`.claude/commands/watch-pr.md:153`](https://github.com/cmk/template-rust/pull/14#discussion_r3172519616) (2026-05-01 07:52 UTC)

This shell snippet now branches on `$auto_fix_count` and `$reply_count`, but those variables aren’t defined anywhere else in this doc. As written, copying/pasting the snippet would fail under `set -u` (or behave unexpectedly if the vars are unset).

Either define how these counts are computed earlier in the workflow, or replace the condition with one that can be derived locally (e.g., based on `git diff`/`git status` and whether replies were posted).

<!-- gh-id: 4210476047 -->
### copilot-pull-request-reviewer[bot] — COMMENTED ([2026-05-01 07:52 UTC](https://github.com/cmk/template-rust/pull/14#pullrequestreview-4210476047))

## Pull request overview

Follow-up fixes to the patch workflow FSM scripts/docs to prevent state divergence and make the tooling work in more environments (e.g., pre-PR review docs and read-only sandboxes).

**Changes:**
- Update `scripts/local_review.sh` to use the supported `codex review --base origin/main` invocation.
- Enhance `scripts/workflow_state.sh` to look for a predicted review file before a PR exists and emit output without heredocs.
- Tighten `scripts/safe_merge.sh` argument rules to prevent guard/merge PR selector divergence; adjust `/watch-pr` docs to avoid staging pull-only review-doc deltas for all-`ask` rounds.

### Reviewed changes

Copilot reviewed 4 out of 4 changed files in this pull request and generated 3 comments.

| File | Description |
| ---- | ----------- |
| scripts/workflow_state.sh | Adds predicted review-file probing (pre-PR) and switches output to `printf` for sandbox compatibility. |
| scripts/safe_merge.sh | Adds a guard intended to reject “flags before selector” invocations to keep the guarded PR consistent with the merged PR. |
| scripts/local_review.sh | Switches to the supported Codex base review invocation (no custom prompt piping). |
| .claude/commands/watch-pr.md | Updates the workflow guidance to avoid staging/pushing pull-only review-doc deltas in all-`ask` rounds. |





<!-- gh-id: 3172530736 -->
#### ↳ cmk ([2026-05-01 07:57 UTC](https://github.com/cmk/template-rust/pull/14#discussion_r3172530736))

Fixed in e852951 — watch-pr.md now defines auto_fix_count and reply_count immediately after triage, before the commit snippet branches on them.

<!-- gh-id: 3172530886 -->
#### ↳ cmk ([2026-05-01 07:57 UTC](https://github.com/cmk/template-rust/pull/14#discussion_r3172530886))

Fixed in e852951 — removed the now-unused plan and calibration context-building blocks from local_review.sh after switching to the supported Codex base-review invocation.
