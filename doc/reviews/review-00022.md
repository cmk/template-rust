# PR #22 — Crate-allowlist law

## Summary

Instantiate cmk's cross-project crate curation as **law** in this
template repo. New repos cloning the template inherit the policy
verbatim; existing first-party repos align in follow-up swap-PRs
filed against each project.

The law has three tiers:

- **Required tier.** Multi-consumer crates listed in
  `[workspace.dependencies]` (above the allowed-tier fence).
  Member crates and downstream repos use them via
  `{ workspace = true }` and never re-state the version.
- **Allowed tier.** Single-consumer crates pinned as **commented**
  entries below the fence in `Cargo.toml` and tabulated in
  `doc/CRATES.md`. Adopting one in a member crate means uncommenting
  the line — no inventing a version pin.
- **Blacklist.** `[[bans.deny]]` entries in `deny.toml`.
  - `anyhow` — libraries must use `thiserror`. Binary-only exemption
    via `wrappers = ["riffgrep"]`.
  - `clap` — `bpaf` won. Preventive (no current first-party clap).
  - `dasp-sample` — direct dep banned to keep
    `Sample`/`ToSample`/`FromSample` out of first-party APIs;
    transitive via cpal still allowed.
  - `async-trait` — workspace MSRV (Rust 1.85) has native
    `async fn in trait`.

### Why now

Cross-project drift was ungoverned: `rand` 0.9/0.10 split between
agogo and upstream transitives, `tokio` features varying per crate,
single-use one-offs (`lofty`, `mlua`, `mimalloc`, `rusqlite`)
scattered without provenance. The full curation + numbers per crate
live in `adat/doc/notes/current-crates.md`; this PR is the codified
output.

### What ships

- `Cargo.toml` — required-tier entries above the fence; allowed-tier
  commented entries below. `tokio` features intentionally unset at
  workspace level (consumers opt in to `["full"]` for binaries or
  narrow features for libraries).
- `deny.toml` — four `[[bans.deny]]` entries with rationales; license
  + sources policies unchanged.
- `AGENTS.md` — new `## Dependency policy` section describing the
  three tiers, the promotion rule (allowed → required when a second
  consumer adopts), and the new-crate flow (PR here).
- `doc/CRATES.md` — protected reference file with the full
  required/allowed/blacklist tables.

### What does NOT ship here

- Mirroring into `adat` (follow-up plan branch).
- Per-project swap-PRs for agogo, connections,
  connections-kani-time-hifi, mcp-live, riffgrep, stdio, stdio-core,
  stdio-staging (filed as a batch once this lands; bodies drafted
  locally in `adat`).
- The future shared numeric/audio/MIDI/time crate (separate design
  effort that will inherit this law and `connections`).

### Test plan

- [x] `cargo deny check` — `advisories ok, bans ok, licenses ok,
      sources ok`. Warnings are pre-existing unused license slots
      plus the expected `unused-wrapper` warning for `riffgrep`
      (riffgrep isn't in this template's dep graph; the warning is
      the correct forward-compatible behavior).
- [x] `cargo test --workspace` — all green.
- [x] `cargo clippy --all-targets -- -D warnings` — clean.
- [x] Pre-commit hook chain (fmt, check_pii, check_layers) — passed
      on the plan commit.

<!-- gh-id: 3200072785 -->
### Copilot on [`doc/plans/plan-2026-05-07-01.md:9`](https://github.com/cmk/template-rust/pull/22#discussion_r3200072785) (2026-05-07 08:42 UTC)

The Goal section says the allowed tier is "commented entries + AGENTS.md table", but the rest of the plan (and the PR) uses `doc/CRATES.md` as the authoritative table with AGENTS.md linking to it. Update this sentence so the plan is internally consistent and matches the shipped artifacts.


<!-- gh-id: 3200072823 -->
### Copilot on [`doc/CRATES.md:22`](https://github.com/cmk/template-rust/pull/22#discussion_r3200072823) (2026-05-07 08:42 UTC)

In the Required tier table, the column header "Workspace features" is used for entries like `default-features = false` (e.g., `hifitime`) and `default-features = false` + a feature list (e.g., `zip`). Those are not features, so the header is misleading. Consider renaming the column (e.g., "Workspace options"), or splitting into separate "Features" vs "Non-default options" columns for clarity.


<!-- gh-id: 3200072848 -->
### Copilot on [`doc/CRATES.md:55`](https://github.com/cmk/template-rust/pull/22#discussion_r3200072848) (2026-05-07 08:42 UTC)

The Required tier section says crates are listed in `[workspace.dependencies]` and cloned downstream, but the `connections` row is a special case (not declared in this template and pinned by git rev downstream). Consider moving `connections` into a separate subsection/footnote (e.g., "Downstream-only required") or adjusting the Required tier definition to explicitly call out this exception so readers don't assume it is present in the template Cargo.toml.

<!-- gh-id: 4242422326 -->
### copilot-pull-request-reviewer[bot] — COMMENTED ([2026-05-07 08:42 UTC](https://github.com/cmk/template-rust/pull/22#pullrequestreview-4242422326))

## Pull request overview

Codifies a cross-project Rust dependency curation policy (“crate allowlist law”) in this template repo so downstream repos inherit consistent workspace pins, an allowed-but-commented tier, and an enforced blacklist via cargo-deny.

**Changes:**
- Reworks root `Cargo.toml` `[workspace.dependencies]` into “required” vs “allowed” (commented) tiers and documents the promotion rule.
- Adds a `cargo-deny` blacklist (`[[bans.deny]]`) for selected crates with rationales.
- Adds/updates policy documentation (`AGENTS.md`, `doc/CRATES.md`) plus associated plan/review records under `doc/`.

### Reviewed changes

Copilot reviewed 6 out of 6 changed files in this pull request and generated 3 comments.

<details>
<summary>Show a summary per file</summary>

| File | Description |
| ---- | ----------- |
| doc/reviews/review-00022.md | Adds PR review record summarizing the policy and verification. |
| doc/plans/plan-2026-05-07-01.md | Adds implementation plan and verification checklist for the policy rollout. |
| doc/CRATES.md | Introduces the authoritative required/allowed/blacklist reference tables. |
| deny.toml | Adds new `[[bans.deny]]` blacklist entries and rationale text. |
| Cargo.toml | Implements required/allowed dependency tiers and removes workspace-level tokio feature selection. |
| AGENTS.md | Documents the three-tier dependency policy and workflow for changes/promotions. |
</details>






<!-- gh-id: 3200128388 -->
#### ↳ cmk ([2026-05-07 08:52 UTC](https://github.com/cmk/template-rust/pull/22#discussion_r3200128388))

Fixed in 795adbd's follow-up: `doc/plans/plan-2026-05-07-01.md` Goal now reads "…allowed-tier (commented entries in `Cargo.toml` + `doc/CRATES.md` reference table linked from AGENTS.md's `## Dependency policy` section)…". Matches the shipped artifacts.

<!-- gh-id: 3200128918 -->
#### ↳ cmk ([2026-05-07 08:52 UTC](https://github.com/cmk/template-rust/pull/22#discussion_r3200128918))

Renamed the column from "Workspace features" to "Workspace options" in both required- and allowed-tier tables. Cells now show the literal toml form (e.g. `features = ["derive"]`, `default-features = false, features = ["deflate"]`), with an explanatory paragraph above the required-tier table noting that empty means defaults-on. Splitting into two columns felt noisier than the single "options" column once the cell content is normalized to the toml syntax.

<!-- gh-id: 3200129725 -->
#### ↳ cmk ([2026-05-07 08:52 UTC](https://github.com/cmk/template-rust/pull/22#discussion_r3200129725))

Pulled `connections` out of the main required-tier table into a new "Required tier — downstream-only" subsection that explicitly states the entry is NOT declared in this template's `Cargo.toml` (would force an external git fetch on every fresh build) and documents the policy: each downstream repo carries the same git rev pin. AGENTS.md's required-tier definition gained a one-line caveat pointing to that subsection, and Cargo.toml's commented `connections` line now explains the "downstream-only" pattern. Also noted in the new subsection that `connections` is the only non-audio domain crate in the law (every other domain dep is audio- or MIDI-flavored), per cmk's framing.
