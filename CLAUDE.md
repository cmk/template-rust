# CLAUDE.md

## What this repo is

<!-- Replace this section with your project description. -->

A Rust workspace with multiple crates.

## Parallel work

At the start of each conversation, ask the user:
"Are any other Claude instances working in this repo right now?"

If yes (or if the user says "work in a worktree"), create a git worktree
before making any changes:

```zsh
git worktree add ../project-<task> -b <branch>
```

Never run two Claude instances in the same worktree. Cargo takes a
file lock on `target/` during each build, so concurrent builds stall
behind each other ("Blocking waiting for file lock"). Separate
worktrees each get their own `target/` and sidestep the lock.

## Architecture

<!-- Replace this section with your architecture overview. -->

### Workspace layout

```
Cargo.toml              — workspace root
crates/
  core/                 — shared types, test utilities, proptest strategies
  cli/                  — binary entrypoint; feature-gates optional lib crates
```

Feature flags on the binary crate's `Cargo.toml` control which library
crates are compiled in:

```toml
[features]
default = ["core"]
core = ["dep:project-core"]
```

## Repository conventions

- **Each commit must leave the repo in a state where `cargo test` passes.**
  Do not commit a library module without the tests that cover it in the
  same commit. Never commit a red test suite.
- **No merge commits.** Always rebase onto main — never `git merge`. The
  history must be linear.
- **CI-repair commits must be fixups.** If a commit on this branch broke
  CI and the follow-up exists only to repair it, commit with
  `git commit --fixup=<broken-sha>` instead of a standalone `fix:`.
  Before pushing, run `scripts/autosquash.sh` (a thin wrapper over
  `GIT_SEQUENCE_EDITOR=: git rebase -i --autosquash origin/main`) so the
  fixups collapse into their targets. This keeps main's linear history
  free of commits that temporarily broke the build. Review-round commits
  (addressing reviewer feedback from an earlier push) remain standalone
  so the audit trail survives.
- **No unsafe code**: every crate root must declare `#![forbid(unsafe_code)]`.
- **Test fixtures are gitignored**, and a fresh checkout must pass
  `cargo test --workspace` with zero setup. Tests that depend on a
  fixture file must use the `fixture_or_skip!` macro from the core
  crate and `return` cleanly when the fixture is absent — **do not**
  `#[ignore]` them and do not panic.
- **Property-based testing is mandatory** for any module that parses,
  encodes, or transforms data. Use `proptest` (workspace dev-dep).
  - Define strategies as functions returning `impl Strategy`, not
    `Arbitrary` derive. Use `prop_oneof!` with frequency weights to
    bias toward boundary values and edge cases.
  - Strategies shared across crates live in `crates/core/src/arb.rs`.
    Strategies local to one module stay colocated in that module's
    `#[cfg(test)]` block.
  - Properties that must hold for a sprint to ship are defined **in
    the plan's Verification table** before any code is written.
  - If a property test blocks progress during implementation, you may
    `#[ignore]` it temporarily **but you must document it** in the
    plan's Review section with the reason and a plan to re-enable.

### Session notes

`doc/notes/` is gitignored and holds the user's personal notes for the
project. Agents may read from it for context but must not write to it
unless explicitly asked.

### Commit style

Conventional commits, present-tense imperative subject. Accepted prefixes:
`feat`, `fix`, `doc`, `test`, `task`, `debt`. Scopes are allowed
(e.g. `doc(skills):`, `fix(scripts):`).

```
feat: Add parser for widget format
fix(codec): Handle timeout on reconnect
test: Add round-trip property tests for codec
doc: Append Sprint 2 completion report
task: Add serde to core dependencies
debt: Remove dead handshake branch
```

Keep subjects under 72 characters. Use the body for non-obvious decisions.

## Two-tier review workflow

### Tier 1 — Local review (pre-push)

The coding agent makes atomic commits as it works. Each commit must pass
`cargo test` and `cargo clippy` (enforced by the pre-commit hook in
`.claude/settings.json`). Commits can be as small as desired.

Before pushing to GitHub, run `/sprint-review`. This spawns an independent
reviewer agent that examines `git diff origin/main...HEAD` and the commit
log. The reviewer flags must-fix issues and follow-ups. The review is
appended to `doc/reviews/review-NNNN.md`, where `NNNN` is the zero-padded
PR number for the branch (use `doc/reviews/review.md` as a placeholder
pre-PR and rename to `review-NNNN.md` once the PR is created).

If must-fix items exist, resolve them before pushing. If the review is
clean, push and create a PR.

### Tier 2 — GitHub review (post-push)

Once pushed, CI runs `cargo test --workspace` and
`cargo clippy --all-targets -- -D warnings` (see
`.github/workflows/ci.yml`). Claude Code Action and/or GitHub Copilot
perform a second-round review on the PR automatically.

After GitHub review activity, run `/pull-reviews <N>` to fetch the PR's
review bodies and inline comments and **append them chronologically to the
same `doc/reviews/review-NNNN.md`** used by Tier 1. The skill is idempotent
— it records `<!-- gh-id: NNNNN -->` markers for each appended item and
skips any id already present, so running it repeatedly only appends new
comments. The result is one file per PR containing the full local + GitHub
review history in order.

Once the findings are addressed in a fix commit and pushed, run
`/reply-reviews <N>` to post short replies to each unresolved comment
thread on GitHub, citing the fix commit SHA. This closes the loop for
the reviewer and leaves an audit trail linking each finding to its
resolution. Re-running `/pull-reviews <N>` afterward mirrors the replies
back into `review-NNNN.md`.

**`review-NNNN.md` rides along with the PR that generated it.** Every
`/pull-reviews` and `/reply-reviews` round that mutates the file must
end in a commit on the PR branch (standalone `doc:` commit or folded
into the round's fix commit). Don't leave it untracked between rounds
— landing it after merge orphans the audit trail. Before final push,
run `/pull-reviews <N>` one last time to capture any trailing comments
and commit the result.

The local review catches design issues and convention violations early.
The GitHub review catches anything that slipped through and validates in
the CI environment. Joining them into a single file per PR preserves the
conversational flow and keeps the review record in one place.

## TDD workflow

Every sprint follows this order:

1. Write the plan to `doc/plans/plan-YYYY-MM-DD-nn.md` before touching source.
   The plan's **Verification** table must list the property tests that
   must pass for the sprint to ship (e.g., "message round-trips through
   encode/decode", "parser never panics on arbitrary input").
2. Create a worktree and branch for the sprint:
   `git worktree add ../project-<sprint> -b sprint/<name>`
3. Write proptest properties and test skeletons that compile but
   trivially fail. Properties come first — they define the contract.
4. Implement the module until all tests are green.
5. Commit on the branch, when green.
6. Run `/sprint-review` against the branch before merging.
7. Rebase and land on main. On the feature branch:
   `git fetch origin && git rebase origin/main`.
   Then fast-forward main:
   `git checkout main && git merge --ff-only <branch>`.
8. Clean up: `git worktree remove ../project-<sprint>`.
9. Append deferred/review sections to the plan document. If any
   property tests were `#[ignore]`d during implementation, document
   the reason and the re-enablement plan here.

### Pre-commit hook

A Claude Code hook in `.claude/settings.json` runs `cargo test` and
`cargo clippy` before every `git commit` tool call. If either fails,
the commit is blocked. This is the automated quality gate; `/sprint-review`
is the manual one.

## Sprint plan format

```markdown
# Plan NN — Title

## Goal
One sentence.

## Dependency Graph
ASCII art showing task dependencies (T1 → T2, T3 → T4, etc.)

## Tasks
Each task is T1, T2, etc. Each task section includes:
- Problem or motivation
- Solution / implementation approach
- Types or API surface

## Verification

### Properties (must pass)
Table of proptest property names, the module they live in, and the
invariant they assert. These are the contract — if a property can't
be satisfied, the sprint isn't done.

| Property | Module | Invariant |
|----------|--------|-----------|
| `msg_round_trips` | `crate_foo::codec` | encode then decode recovers original |

### Spot checks
Table of unit test names + specific assertions.

### Build gates
- cargo build — no errors
- cargo test — all pass (no `#[ignore]` without Review documentation)
- cargo clippy --all-targets — no errors
- End-to-end scenario description

## Deferred
What was intentionally left out and why.

## Review
- Any `#[ignore]`d properties: which ones, why, re-enablement plan
- Design deviations from the plan
- Recommendations
```
