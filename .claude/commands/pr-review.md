---
description: Tier-1 local pre-push code review. Invokes scripts/pr_review.sh, which runs codex review against origin/main and appends findings to doc/reviews/review-NNNNN.md. The agent does not author the reviewer prompt.
argument-hint: (no args)
---

# PR Review — Tier 1 (Local)

You are orchestrating the Claude Code implementation of the
`plan_finalized → local_reviewed` FSM transition: a **local, pre-push**
code review. This is Tier 1 of a two-tier system:

- **Tier 1 (this command):** `scripts/pr_review.sh` runs `codex review
  --base origin/main` against the branch. Codex auto-loads `AGENTS.md`
  + `doc/reviews/calibration.md` from disk as its system prompt.
  Output is appended to `doc/reviews/review-NNNNN.md`.
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

## Step 0: Autosquash any pending fixups

Per AGENTS.md, CI-repair commits are made as `--fixup`s and must be
collapsed before review/push. Refresh the remote-tracking ref first so
the check isn't against a stale base, then scan for fixups:

```
git fetch --quiet origin main
git -c color.ui=never log --oneline origin/main..HEAD | grep -E '^[0-9a-f]+ fixup!' || true
```

If any fixups exist, run `scripts/git_squash.sh` to collapse them.
Abort if the working tree is dirty (the script checks this). After
autosquash, re-run the fixup check to confirm the branch is clean.

## Step 1: Verify prerequisites

The review always targets the current branch against `origin/main`.
Refresh the ref and confirm the branch has diverged:

```
git fetch --quiet origin main
git diff origin/main...HEAD >/dev/null && echo "no diff to review" || true
```

If `git diff --quiet origin/main...HEAD` exits 0, abort — there's
nothing to review.

**Verify the review file exists.** `pr_review.sh` appends to a file
created by TDD step 7; it never creates the file itself. Get its
path:

- If a PR already exists for this branch:
  ```
  scripts/pr_report.py path "$(gh pr view --json number --jq .number)"
  ```
- Otherwise (the normal pre-push case):
  ```
  scripts/pr_report.py path
  ```

`pr_report.py path` predicts (or accepts) the PR number and emits the
zero-padded filename. Confirm the returned path exists **and contains
a `## Summary` section**. If either is missing, abort and tell the
user to run TDD step 7. Do not create the file yourself — the PR body
belongs in step 7's commit, not as a post-hoc fabrication.

## Step 2: Run codex via scripts/pr_review.sh

Invoke `scripts/pr_review.sh`. It runs `codex review --base
origin/main`, reads `AGENTS.md` automatically as the reviewer system
prompt (that's the contract — the reviewer's instructions live in
`AGENTS.md` and `doc/reviews/calibration.md` on disk, not in this
file), and appends a `## Local review (YYYY-MM-DD)` section to the
review file.

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
triage it. No interpretation, no summarization — pass it through
verbatim to the triage logic. (`tail` from a recorded byte-offset, or
re-read the file and slice from the last `## Local review` heading
onward.)

## Step 4: Triage and apply auto-fixable items

For each item in the codex review's **Must fix before push** and
**Follow-up (future work)** sections, classify into exactly one
bucket — same heuristic as `/pr-watch`:

- **auto** — change is local (one file, under ~20 lines),
  non-destructive (no API removal, no file deletion), and does not
  require cross-module reasoning. Doc nits, missing imports, dead
  arms, off-by-one in comments, narrow logic fixes, small test
  additions. Apply now.
- **needs-user** — larger scope, judgment calls, design decisions,
  cross-module refactors, or anything where you'd hesitate.
  **Do not apply.** Surface in the report.

When in doubt, classify as **needs-user** (a miscategorized auto-fix
ships wrong code; a miscategorized needs-user only delays one
iteration until the user resolves it).

### Apply the auto bucket

Apply each auto-bucket item to the working tree. Stay strictly within
the scope of the reviewer's comment — no adjacent cleanup, no "while
I'm here" changes. If multiple items touch the same file, batch the
edits before running tests.

Then commit:

```
git add <edited files>
git commit -m "<prefix>: Address pr-review feedback"
```

Use the prefix that matches the nature of the fixes:
`fix:` (bug), `debt:` (mechanical cleanup), `test:` (test additions),
`doc:` (doc nits). Mix-and-match isn't possible in one commit — if
the auto items split across categories, pick the predominant one.

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
