---
description: Tier-1 local pre-push code review. Invokes scripts/pr_review.sh, which runs codex review against origin/main, appends findings to doc/reviews/review-NNNNN.md, and commits the review artifact as a finalized-doc fixup. The agent does not author the reviewer prompt.
argument-hint: (no args)
---

# PR Review — Tier 1 (Local)

You are orchestrating the Claude Code implementation of the
`plan_finalized → local_reviewed` FSM transition: a **local, pre-push**
code review. This is Tier 1 of a two-tier system:

- **Tier 1 (this command):** `scripts/pr_review.sh` runs `codex review
  --base origin/main` against the branch. Codex auto-loads `AGENTS.md`
  + `doc/reviews/calibration.md` from disk as its system prompt.
  Output is appended to `doc/reviews/review-NNNNN.md` and committed
  as a fixup to the finalized-doc commit.
- **Tier 2 (GitHub):** After push, CI runs `cargo test --workspace`
  and `cargo clippy --all-targets -- -D warnings` (see
  `.github/workflows/ci.yml`). Claude Code Action and/or Copilot
  review the PR on GitHub.

**Your role is the orchestrator, not the reviewer.** You run
prerequisite checks, invoke the script, read back what codex wrote,
and triage auto-fixable items. You do **not** author a reviewer
prompt. You do **not** spawn a Claude subagent. You do **not** gather
context to feed an agent — codex picks up the contract files itself.
Anything you do beyond running the script is the failure mode this
command exists to prevent: the agent shaping its own review.

---

## Step 0: Check pending fixups

Per AGENTS.md, mechanical repairs are made as `--fixup`s. They may
remain transient during review, but they must be collapsed before
merge by `scripts/git_autosquash_finalize.sh`. Refresh the
remote-tracking ref first so the check isn't against a stale base,
then scan for fixups:

```
git fetch --quiet origin main
git -c color.ui=never log --oneline origin/main..HEAD | grep -E '^[0-9a-f]+ fixup!' || true
```

If fixups exist, do not squash them as part of `/pr-review`; they are
expected until finalization. If the branch is otherwise ready to merge,
run `scripts/git_autosquash_finalize.sh` instead of this command.

## Step 1: Verify prerequisites

The review always targets the current branch against `origin/main`.
Refresh the ref and confirm the branch has diverged:

```
git fetch --quiet origin main
if git diff --quiet origin/main...HEAD; then
  echo "no diff to review" && exit 1
fi
```

`git diff --quiet` exits 0 when there is no diff — that's the abort
condition. Plain `git diff` always exits 0 on a successful run and
would not detect divergence.

Review-file selection and validation belong to `scripts/pr_review.sh`.
Do not run a separate `scripts/pr_report.py path` existence gate in
this command. The predicted next PR number can drift between TDD step 7
and this transition; the script first looks for exactly one
branch-local `doc/reviews/review-NNNNN.md` in
`git diff origin/main...HEAD`, then falls back to the predicted path.
It also validates that the chosen file exists and contains `## Summary`.
If that validation fails, surface the script's error and stop.

## Step 2: Run codex via scripts/pr_review.sh

Invoke `scripts/pr_review.sh`. It runs `codex review --base
origin/main`, reads `AGENTS.md` automatically as the reviewer system
prompt (that's the contract — the reviewer's instructions live in
`AGENTS.md` and `doc/reviews/calibration.md` on disk, not in this
file), appends a `## Local review (YYYY-MM-DD)` section to the review
file, and commits that review artifact as a fixup to the commit that
created the finalized review doc.

**Do not author a prompt. Do not pass context to a subagent. Do not
launch an agent yourself.** The orchestrator (you) has zero authoring
role in how the diff is handed off — the reviewer is codex; codex's
prompt is `AGENTS.md` + `doc/reviews/calibration.md` on disk; the
script wires them together. Anything you do beyond running the
script is the failure mode this command exists to prevent.

If `pr_review.sh` exits non-zero, surface stderr and stop. Do not
retry with hand-rolled inputs. Do not invent a reviewer prompt
yourself.

## Step 3: Read back the appended review section

Capture the section codex appended to the review file so Step 4 can
triage it. Use the review path printed by `pr_review.sh` after a
successful run. No interpretation, no summarization — pass it through
verbatim to the triage logic. (`tail` from a recorded byte-offset, or
re-read the file and slice from the last `## Local review` heading
onward.)

## Step 4: Triage and apply auto-fixable items

For each item in the codex review's **Must fix before push** and
**Follow-up (future work)** sections, classify into exactly one
bucket — same heuristic as `/pr-watch` and the
[gardener rule](../../AGENTS.md#the-gardener-rule):

- **auto** — change is local (one file, under ~20 lines),
  non-destructive (no API removal, no file deletion), and does not
  require cross-module reasoning. Doc nits, missing imports, dead
  arms, off-by-one in comments, narrow logic fixes, small test
  additions. Apply now.
- **needs-user** — larger scope, judgment calls, design decisions,
  cross-module refactors, incorrect findings, or anything where you'd
  hesitate.
  **Do not apply.** Surface in the report.

When in doubt, classify as **needs-user** (a miscategorized auto-fix
ships wrong code; a miscategorized needs-user only delays one
iteration until the user resolves it).

Treat "optional", "nit", "follow-up", suppressed, and low-confidence
comments as normal comments during this classification. If they are
local, correct, and small, they are **auto**; defer only with an
explicit reason.

### Apply the auto bucket

Apply each auto-bucket item to the working tree. Stay strictly within
the scope of the reviewer's comment — no adjacent cleanup, no "while
I'm here" changes. If multiple items touch the same file, batch the
edits before running tests.

Then commit. Mechanical local-review cleanups use fixups by default:

```
git add <edited files>
git commit --fixup=<latest-implementation-commit>
```

Use the latest non-plan, non-review-doc implementation commit as the
default target. If the reviewer feedback changes design or follow-up
behavior rather than mechanically repairing an existing commit, use a
standalone `fix:` or `feat:` commit instead. If there are no
auto-fixes, do not make another commit; `pr_review.sh` already
committed the local-review artifact as a doc fixup.

The pre-commit hook runs `cargo fmt --check`, `scripts/check_pii.sh`,
and `scripts/check_layers.sh`. The pre-push hook runs
`cargo test --workspace` and `cargo clippy --all-targets -- -D warnings`.
If either fails:

- Read the failure. If a specific auto-fix caused the breakage,
  revert that one edit, reclassify the corresponding item as
  **needs-user**, and retry the commit.
- If the commit still fails: leave the working tree dirty so the
  user can investigate. Surface the failure in the report.

**Do not loop `/pr-review` recursively.** One pass of auto-fixes is
the contract — the agent applies what it confidently can, then hands
off. The user can re-run `/pr-review` for another pass if they want
one.

## Step 5: Report and hand off

Print a structured summary, ≤ 15 lines:

```
pr-review for <branch>
  must-fix items:        <total>
    auto-applied:        <n>
    needs you:           <m>   ← these need your decision
      - path:line — one-line summary
      - path:line — one-line summary
  follow-ups (auto-applied): <n>
  follow-ups (deferred):     <n>   ← tracked, not blocking
  fix commit:            <sha> (or: "no commit — all needs-user")
```

Then:

- **If zero `needs-user` items remain:** branch is clear to push.
  Offer to push and open the PR (but don't do it without
  confirmation):
  ```
  gh pr create --title "<title>" \
    --body-file <(scripts/pr_report.py body NNNNN)
  ```
  This makes the GitHub body a direct copy of the `## Summary`
  section — the two can't drift. Tier 2 (CI + GitHub review) runs
  automatically on the PR.

- **If `needs-user` items remain:** the user reads the review file
  and decides which ones to fix, push back on, or defer. Don't push.
  Don't auto-fix the needs-user items.
