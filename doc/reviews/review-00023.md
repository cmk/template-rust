# PR #23 — Port connections review-prompt sharpening upstream

## Summary

- Add §Review-skepticism to AGENTS.md (codex's system prompt) and Patterns 9–10 to calibration.md so codex audits trait/contract claims, escalates `*_total`/`*_relaxed` test renames, and treats the plan §Review as adversarial framing rather than ratifying it.
- Gut `.claude/commands/pr-review.md` (–225/+66): the Claude path is now a thin shim that runs `scripts/pr_review.sh` (which delegates to codex). The orchestrator authors no prompt, picks no model, and gathers no context — codex loads the contract files itself.
- Tighten `.github/instructions/docs-review.instructions.md`: `doc/reviews/review-*.md` is off-limits (audit trail, not a doc that asks for review), the bar for other docs is raised to four hard categories with default-silence, the `nit:` tier is removed, and §Plan-doc skepticism lands as a fifth flag category. `scripts/pr_review.sh` now records an AGENTS.md / calibration.md fingerprint in each appended local-review section.

## Test plan

- [x] `cargo fmt --all -- --check`
- [x] `cargo test --workspace` (no Rust changed; ran for completeness via pre-commit/-push hooks across each commit)
- [x] `python3 -m unittest discover -s tests` (4/4 pass)
- [x] `scripts/check_pii.sh`
- [x] `scripts/check_layers.sh`
- [x] `scripts/pr_review.sh --check` (codex / gh / pr_report.py reachable)
- [ ] Tier-2 smoke test: GitHub Copilot review on this PR exercises the new `docs-review.instructions.md` rules — verify it surfaces zero findings on `review-00023.md`, raises the bar on the other docs, and (on a future plan PR) catches a §Review-shaped ratification trap.
- [ ] Manual smoke test: run `/pr-review` on a synthetic branch with an `iso!` whose closure breaks `<=` on NaN, a `*_total` proptest rename, and a §Review note explaining the rename — confirm codex flags the type-claim gap as must-fix.

<!-- gh-id: 4249740297 -->
### copilot-pull-request-reviewer[bot] — COMMENTED ([2026-05-08 05:35 UTC](https://github.com/cmk/template-rust/pull/23#pullrequestreview-4249740297))

## Pull request overview

This PR ports and tightens the repository’s review workflow contracts so automated reviews are more skeptical of plan/§Review framing, and it simplifies the Claude `/pr-review` command to delegate Tier‑1 review execution to `scripts/pr_review.sh` (which runs `codex review`).

**Changes:**
- Add “Review skepticism” rules to `AGENTS.md` and extend `doc/reviews/calibration.md` with two new anti-ratification patterns.
- Simplify `.claude/commands/pr-review.md` to an orchestrator shim that runs `scripts/pr_review.sh` rather than constructing/spawning a separate reviewer agent.
- Tighten docs review instructions, including an explicit scope exclusion for `doc/reviews/review-*.md`, and add a prompt fingerprint banner to `scripts/pr_review.sh`.

### Reviewed changes

Copilot reviewed 7 out of 7 changed files in this pull request and generated 2 comments.

<details>
<summary>Show a summary per file</summary>

| File | Description |
| ---- | ----------- |
| `scripts/pr_review.sh` | Appends a prompt fingerprint (AGENTS/calibration blob IDs) to the local review section for traceability. |
| `doc/reviews/review-00023.md` | Adds the PR’s audit-trail entry (summary + test plan). |
| `doc/reviews/calibration.md` | Adds Patterns 9–10 to calibrate reviewers against “type-claim vs relaxed test” and §Review framing traps. |
| `doc/plans/plan-2026-05-07-04.md` | Adds the implementation plan describing the upstream port and verification steps. |
| `AGENTS.md` | Adds a new “Review skepticism” subsection to strengthen reviewer obligations (audit, escalation, adversarial §Review framing). |
| `.github/instructions/docs-review.instructions.md` | Raises the bar for doc findings, excludes `doc/reviews/review-*.md`, and adds plan §Review skepticism checks. |
| `.claude/commands/pr-review.md` | Replaces the prior subagent-driven reviewer flow with a script-driven codex review workflow. |
</details>






<!-- gh-id: 3206503578 -->
### Copilot on [`scripts/pr_review.sh:74`](https://github.com/cmk/template-rust/pull/23#discussion_r3206503578) (2026-05-08 05:35 UTC)

The prompt fingerprint is computed after running `codex review`, but the comment says it's recording what codex "saw". To make the fingerprint reliably correspond to the exact prompt version used for the review (and match the stated intent), compute `agents_sha`/`calib_sha` before invoking `codex review` and then print them alongside the captured output.

<!-- gh-id: 3206503595 -->
### Copilot on [`.claude/commands/pr-review.md:53`](https://github.com/cmk/template-rust/pull/23#discussion_r3206503595) (2026-05-08 05:35 UTC)

`git diff origin/main...HEAD` exits 0 even when there *are* changes (unless `--quiet/--exit-code` is used), so this snippet will incorrectly echo "no diff to review" on most branches. Use `git diff --quiet origin/main...HEAD` (or `git diff --exit-code ...`) for the divergence check so the instructions match the abort condition described below.


<!-- gh-id: 3206552740 -->
#### ↳ cmk ([2026-05-08 05:48 UTC](https://github.com/cmk/template-rust/pull/23#discussion_r3206552740))

Fixed — moved the fingerprint compute above the codex invocation so the recorded SHAs are guaranteed to match the version codex loaded. Comment updated to match.

<!-- gh-id: 3206553859 -->
#### ↳ cmk ([2026-05-08 05:48 UTC](https://github.com/cmk/template-rust/pull/23#discussion_r3206553859))

Fixed — replaced the snippet with the `--quiet` form that matches the abort prose below it. The wrong snippet would have echoed 'no diff to review' on every branch with changes.
