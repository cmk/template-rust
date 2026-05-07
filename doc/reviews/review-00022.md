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
