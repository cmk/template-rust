# AGENTS.md

`AGENTS.md` is the shared instruction file for Codex, Claude Code, and
other coding agents. `CLAUDE.md` is a compatibility symlink back to this
file. Claude Code-specific commands and settings remain under `.claude/`.

## What this repo is

A Rust workspace template. Downstream repos (one per workspace) are
seeded from this template and resync the workflow tooling via
`scripts/template_sync.sh`.

## Architecture

```
Cargo.toml              — workspace root
rust-toolchain.toml     — pinned Rust 1.88 + components
rustfmt.toml            — formatter config (edition 2024)
deny.toml               — cargo-deny policy
crates/
  project/              — public facade crate; exposes `project::core`
  core/                 — shared types, test utilities, proptest strategies
  cli/                  — binary entrypoint; feature-gates optional lib crates
```

Feature flags on the facade and binary crates control which library
crates are compiled in:

```toml
[features]
default = ["core"]
core = ["dep:project-core"]
```

Bumping MSRV requires updating three places together: `rust-version` in
`Cargo.toml`, the channel in `rust-toolchain.toml`, and the action ref
in `.github/workflows/ci.yml`.

`doc/notes/` is gitignored and holds the user's personal notes. Agents
may read from it for context but must not write to it unless asked.

## Syncing downstream forks

Downstream repos drift on the workflow tooling that template-rust owns
canonically: `scripts/`, `.githooks/`, the Claude command playbooks, the
audit/workflow prose, and the Python regression suite.
`scripts/template_sync.sh` is a manifest-driven manual sync — pull-mode
(maintainer runs it from this repo against one or more downstream
paths), opt-in `--apply`. It reports match / drift / missing for the
verbatim set, and match / differs / missing for the surgical set, but
never auto-edits surgical paths.

Surgical paths the maintainer still owes by hand: `AGENTS.md`,
`Cargo.toml`, `rust-toolchain.toml`, `rustfmt.toml`, `deny.toml`,
`.github/workflows/ci.yml`. They encode project-specific facts (MSRV,
crate names, layer rules, dependency policy) and need a human merge.

```
# Read-only drift check across one or more downstream repos:
scripts/template_sync.sh ../downstream-a ../downstream-b

# After reviewing the report, land the verbatim subset:
scripts/template_sync.sh --apply ../downstream-a
```

`--apply` refuses a dirty downstream tree so the resulting `git diff`
is exactly the sync, ready to land via the normal `plan/YYYY-MM-DD-NN`
branch in the downstream.

## Library conventions

- **No unsafe code**: every crate root declares `#![forbid(unsafe_code)]`.
- **Inter-module imports respect a partial order** (pre-commit hook).
  `project-core` (`crates/core/src`) starts with:

      test -> conn
      conn -> (leaf)

  `project-cli` (`crates/cli/src`) starts with:

      command -> parse
      parse   -> (leaf)

  Each top-level module-root file declares its allowed deps in a
  sentinel header:

      //! layer: test
      //! depends-on: conn

  `scripts/check_layers.sh` parses these and fails on any layer import
  through `crate::<top>`, the crate's own extern name (e.g.
  `project_core::<top>`), or a facade path (`project::core::<top>`)
  not listed in the current layer's `depends-on:`. Adding an edge
  requires updating both the sentinel and this rule's prose.
- **Test fixtures are gitignored**; a fresh checkout passes
  `cargo test --workspace` with zero setup. Fixture-dependent tests
  use the `fixture_or_skip!` macro and `return` cleanly when absent —
  **do not** `#[ignore]` them and do not panic.
- **Property-based testing is mandatory** for any module that parses,
  encodes, or transforms data (`proptest` workspace dev-dep):
  - Strategies are functions returning `impl Strategy`, not `Arbitrary`
    derive. Use `prop_oneof!` with frequency weights to bias toward
    boundary values.
  - Cross-crate strategies live in `crates/core/src/arb.rs`. Module-local
    strategies stay in that module's `#[cfg(test)]` block.
  - Sprint-blocking properties go in the plan's **Verification** table
    before any code is written. Temporary `#[ignore]` requires a
    Review-section reason and re-enable plan.
- **Modern module layout** (no `mod.rs` — sibling file one level up,
  named after the directory). Document any deviation.

## Dependency policy

This template is the source of truth for which external crates may
appear in any first-party Cargo.toml. Three tiers:

1. **Required tier.** Listed in `[workspace.dependencies]` (above the
   allowed-tier fence). Two or more first-party consumers. Member crates
   and downstream repos use them via `{ workspace = true }`; never
   re-state the version. **Exception:** `connections` is required-tier
   policy but isn't declared in this template's `Cargo.toml` — each
   downstream pins the same git rev directly. See `doc/CRATES.md`.
2. **Allowed tier.** Listed below the fence as **commented** entries,
   tabulated in `doc/CRATES.md`. Single-consumer crates pinned to the
   canonical version. To adopt one, uncomment the line here and add
   `{ workspace = true }` in the member's Cargo.toml — do not invent
   your own version pin.
3. **Blacklist.** `[[bans.deny]]` in `deny.toml`. Currently:
   - `anyhow` — libraries use `thiserror`. Binary-only exemption via
     `wrappers = [...]`.
   - `clap` — `bpaf` won. Preventive.
   - `async-trait` — Rust 1.88 has native `async fn in trait`. Use
     `-> impl Future<Output = ...> + Send` where Send bounds are
     required.

**Promotion.** When an allowed-tier crate gains a second consumer, PR
here moves its line above the fence and updates `doc/CRATES.md`.

**New crates.** PR to template-rust adds the entry and updates
`doc/CRATES.md`. The PR is the place to argue why the crate earns its
spot. Until it lands, the crate may not appear in any first-party
Cargo.toml.

`cargo deny check` enforces the blacklist; required-vs-allowed is a
code-review job. The `multiple-versions = "warn"` rule in `deny.toml`
surfaces drift.

## Repository conventions

### Parallel work

At the start of each conversation, ask: "Are any other agent instances
working in this repo right now?" If yes, a worktree is **mandatory** —
two agents in the same worktree stall on cargo's `target/` lock. Naming:
`../<repo>.plan-YYYY-MM-DD-NN` + branch `plan/YYYY-MM-DD-NN` (TDD
step 1).

Verify worktrees aren't sharing `target/` (would happen if
`CARGO_TARGET_DIR` is set or `~/.cargo/config.toml` overrides
`build.target-dir`):
`cargo metadata --format-version 1 --no-deps | jq -r .target_directory`
in each — different paths = safe.

### The gardener rule

Weeds are weeds, regardless of who planted them. Whenever you spot a
violation of any rule above — stale comment, mis-bounded proptest
generator, lying `expect()` string, undocumented `#[ignore]`, missing
verification-table property — flag it even if you didn't write it.

- **Flag** in the plan's `## Review` section: `file:line — rule —
  consequence`.
- **Fix** if local, single-file, no API change, no scope expansion —
  ask the user before merging.
- **Defer** otherwise — name the cleanup specifically enough for the
  next plan branch to pick up.

Review labels ("optional", "nit", "follow-up", suppressed,
low-confidence) are not discounts. Treat with the same seriousness;
defer only when large, complex, outside the sprint, or incorrect.

CI gates (fmt, clippy, gitleaks, the `check_*.sh` scripts) catch their
own drift. The gardener rule covers what lives *below* the gate: prose,
doc links, decorative tests, mis-bounded generators, stale section
headers, panic strings that contradict preconditions, deferred
Verification-table properties.

### Git hooks

Hooks are activated by `git config core.hooksPath .githooks`. Bypass
(`--no-verify`) only when explicitly authorized; CI re-runs the same
gates plus a `gitleaks` history scan as defense-in-depth.

- **Each pushed commit must be green.** `pre-push` runs
  `cargo test --workspace` + `cargo clippy --all-targets -- -D warnings`.
  Intra-branch commits can be transiently red — pre-push is the gate,
  CI is the source of truth for `origin/main`'s bisect property.
  `pre-commit` runs the cheap chain on every commit:
  `cargo fmt --check`, `check_pii.sh`, `check_layers.sh`. There's
  also an agent `PreToolUse` layer in `.claude/settings.json` that
  catches PII drift on agent-invoked `git commit*` — but use separate
  `git add` and `git commit` calls, since chained `add && commit` sees
  an empty pre-add diff and slips through.
- **No merge commits.** Always rebase onto main; history is linear.
- **Mechanical repair commits are fixups.** CI repairs, local-review
  cleanups, and GitHub review rounds that do not change design use
  `git commit --fixup=<sha>` against the implementation commit they
  repair. Review-doc mirror changes use a separate fixup targeting
  the finalized-doc commit. Design-changing feedback may stay as a
  standalone `fix:` or `feat:` commit. Run
  `scripts/git_autosquash_finalize.sh` before merge.

### Sprint workflow

The sprint workflow is a finite state machine, not a menu. The full
review-round lifecycle and `/pr-watch` loop are diagrammed in
`doc/workflow.md` (the prose here is authoritative if the two
disagree). Identify the current state before committing, running
local review, pushing, replying, or merging — take only the documented
transition. Use `scripts/workflow_state.sh` when the state isn't
obvious.

```
main_clean → on_branch → plan_committed → impl_green → plan_finalized
  → local_reviewed → pushed → gh_review → items_pulled → round_unpushed
  → gh_review → autosquash_finalized → merged
```

Workflow-sensitive actions go through repo scripts/commands:

- Local review: `/pr-review` (Claude Code) or `scripts/pr_review.sh`.
  `/review` is post-push help, **not** the canonical pre-push transition.
- PR body: `scripts/pr_report.py path` / `body`.
- GitHub review ingestion: `scripts/pr_report.py reviews`.
- Replies: `/pr-reply` (wraps `scripts/pr_reply.py` + `pr_report.py reviews`).
- Finalization: `scripts/git_autosquash_finalize.sh`.
- Merge: `scripts/git_merge.sh`, **not** `gh pr merge`.

When a `gh`-backed command errors (auth prompt, network, missing
permission), surface the error — **don't silently fall back** to git
plumbing or MCP tools. They almost always do the wrong thing for
GitHub-side state.

### Test-driven development (TDD) workflow

A plan at `doc/plans/plan-YYYY-MM-DD-NN.md` maps to branch
`plan/YYYY-MM-DD-NN` and (optionally) worktree
`../<repo>.plan-YYYY-MM-DD-NN`. One slug, three places.

1. **Pick the filename.** `ls doc/plans/plan-YYYY-MM-DD-*.md` to find
   the next unused `NN`. No writes yet — main stays clean.
2. **Worktree or branch?** Worktree if another agent is active, else
   user's call. `git worktree add ../<repo>.plan-YYYY-MM-DD-NN -b
   plan/YYYY-MM-DD-NN` or `git switch -c plan/YYYY-MM-DD-NN`.
3. **Write the plan.** The Verification table lists property tests
   that must pass to ship. Commit as `plan: <one-line goal>`.
4. Write proptest properties + test skeletons that compile but fail.
5. Implement until green.
6. Commit on the branch when green.
7. **Finalize sprint docs** in one commit: append Deferred/Review
   sections to the plan; create the review file at
   `$(scripts/pr_report.py path)` with `# PR #<N> — <title>` +
   `## Summary` (the PR body, written for a human reviewer — not a
   ship-report). `review-00000.md` is a protected sentinel; real
   reviews start at `00001`. Commit as `doc: Finalize plan NN and PR
   description`. **Must precede local review** — the local-review
   command aborts if `## Summary` is missing.
8. Run `/pr-review` (or `scripts/pr_review.sh`).
9. Open the PR:
   `gh pr create --body-file <(scripts/pr_report.py body N)`.
10. Before merge, run `scripts/git_autosquash_finalize.sh`. It
    autosquashes fixup commits, reruns full gates, and force-pushes
    the cleaned branch with lease.
11. Rebase + land: `git fetch origin && git rebase origin/main`, then
    `git merge --ff-only`. (Worktree case: main is checked out in the
    *primary* worktree, so run the merge from there.)
12. `git worktree remove ...` (if used), then `git branch -d ...`.

### Code review

#### Tier 1 — Local (pre-push)

Before pushing, run `/pr-review` (or `scripts/pr_review.sh`). It
examines `git diff origin/main...HEAD`, appends a
`## Local review (YYYY-MM-DD)` section, commits that artifact as a
fixup to the finalized-doc commit, and aborts if the review file or
`## Summary` is missing.

If another PR opens between TDD step 7 and your push, the predicted
review number can drift — re-run `scripts/pr_report.py path` and `mv`
the file if needed.

#### Tier 2 — GitHub (post-push)

CI runs tests + clippy. Auto-review agents and Copilot review the PR.

After GitHub review activity:
1. `/pr-report <N>` fetches comments and **appends** them to
   `review-NNNNN.md` (idempotent via `<!-- gh-id: NNNNN -->` markers).
2. Address findings as **uncommitted edits** in the working tree.
3. `/pr-reply <N>` posts replies, mirrors them into the doc, and
   creates one or two commits for the round:
   code/test/product-doc mechanical fixes as `fixup! <implementation>`,
   review-doc mirror changes as `fixup! <finalized-doc>`.
   Design-changing feedback may be a standalone `fix:` or `feat:`
   commit, still paired with a review-doc fixup when the mirror changed.
4. `git push` once.

**Do not pre-commit the fix** — `/pr-reply` expects to start from
`gh_review` (local at-or-behind origin) and produce the round commits
itself. **Do not merge from `round_unpushed` or before
`autosquash_finalized`** — `gh pr merge` is GitHub-side and silently
drops local commits, while unsquashed fixups should not reach main.
Use `scripts/git_merge.sh`, which refuses if the branch is ahead of
origin or the PR head still contains autosquashable commits. Recovery
(if a merge already dropped a round commit): cherry-pick the stranded
SHA into the next plan branch's first commit; don't open a tiny
standalone PR.

#### Automated poll loop (optional)

`/loop 10m /pr-watch <N>` runs the round cycle on a timer. Each tick
either heartbeats, auto-fixes trivially-clear items + runs the
`/pr-reply` flow + pushes the transient fixup round, or pauses on push failure. Auto-fix scope:
one file, < 20 lines, no API removal, no cross-module reasoning —
anything ambiguous is surfaced as **needs you**. The loop **never
merges** — that's the user's manual gate. See `doc/workflow.md` →
*`/pr-watch` dynamic-mode loop* for the per-tick state diagram.

### Commit style

Conventional commits, present-tense imperative subject. Accepted
prefixes: `plan`, `feat`, `fix`, `fmt`, `doc`, `test`, `task`, `debt`.
Scopes allowed (`doc(skills):`, etc.). Sprint-opener is a `plan:`
commit adding the plan doc; subsequent commits cover the
implementation.

```
plan: Widget-format parser, sprint goals and verification table
feat: Add parser for widget format
fix(codec): Handle timeout on reconnect
test: Add round-trip property tests for codec
debt: Remove dead handshake branch
```

Keep subjects under 72 characters. Use the body for non-obvious
decisions.

## Sprint plan format

```markdown
# Plan NN — Title

## Goal
One sentence.

## Dependency Graph
T1 → T2, T3 → T4, ...

## Tasks
T1, T2, ... — each with: problem/motivation, solution/approach,
types or API surface.

## Verification

### Properties (must pass)
| Property | Module | Invariant |
|----------|--------|-----------|
| `msg_round_trips` | `crate_foo::codec` | encode then decode recovers original |

### Spot checks
Unit test names + specific assertions.

### Build gates
- cargo build, test, clippy --all-targets — all clean
- End-to-end scenario description

## Deferred
What was intentionally left out, why.

## Review
- Any `#[ignore]`d properties — which, why, re-enablement plan
- Design deviations from the plan
- **Drift caught** (file:line — rule — fixed-here / deferred). See
  the gardener rule.
- Recommendations
```
