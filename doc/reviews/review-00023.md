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
