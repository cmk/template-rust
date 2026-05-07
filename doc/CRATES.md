# CRATES.md — dependency tiers reference

Authoritative tables for the three-tier dependency policy described in
`AGENTS.md` → `## Dependency policy`. Source of truth for which
external crates may appear in any first-party Cargo.toml.

This file is **protected** in the sense agents use the term — do not
write to it without authorization. Promoting a crate from allowed →
required, adding a new crate, or modifying the blacklist all happen
via PR to this repo.

The corresponding `[workspace.dependencies]` entries live in
`Cargo.toml`; the corresponding bans live in `deny.toml`.

---

## Required tier

Multi-consumer crates. Member crates use `{ workspace = true }`;
downstream repos clone the same Cargo.toml entries.

| Crate | Pin | Workspace features | Why required |
|---|---|---|---|
| `serde` | `1` | `derive` | universal |
| `serde_json` | `1` | — | universal |
| `thiserror` | `2` | — | universal |
| `tokio` | `1` | (none — consumers opt in) | universal |
| `tracing` | `0.1` | — | universal |
| `tracing-subscriber` | `0.3` | `env-filter` | shared logging baseline |
| `proptest` (dev) | `1` | — | testing baseline (mandated) |
| `tempfile` (dev) | `3` | — | shared scratch-fs |
| `assert_cmd` (dev) | `2` | — | binary integration tests |
| `predicates` (dev) | `3` | — | pairs with assert_cmd |
| `insta` (dev) | `1` | — | snapshot tests |
| `trybuild` (dev) | `1` | — | macro / compile-fail tests |
| `fixed` | `1` | — | numeric base |
| `time` | `0.3` | — | re-exported via connections |
| `hifitime` | `4.3` | `default-features = false` | re-exported via connections |
| `midir` | `0.10` | — | MIDI I/O |
| `rosc` | `0.11` | — | OSC encode/decode |
| `rust-fsm` | `0.7` | — | state machines |
| `bpaf` | `0.9` | `derive` | CLI parser |
| `uuid` | `1` | (consumers pick v4/v7/serde) | id |
| `mdns-sd` | `0.12` | — | service discovery |
| `russh` | `0.49` | — | SSH client |
| `quick-xml` | `0.36` | `serialize` | XML |
| `flate2` | `1` | — | gzip |
| `zip` | `8` | `default-features = false`, `deflate` | archive |
| `xz2` | `0.1` | — | xz |
| `sha1` | `0.10` | — | hashing |
| `futures` | `0.3` | — | Stream / async utilities |
| `ignore` | `0.4` | — | gitignore-aware walk |
| `rand` | `0.10` | — | RNG (single major workspace-wide) |
| `rmcp` | `1.4` | (consumers pick) | MCP |
| `connections` | git rev | — | shared base for time/numeric (downstream repos pin a rev; not declared here in the template) |

`tokio` features are intentionally unset at workspace level. Binaries
opt into `["full"]` at the consumer site; libraries pick narrow
features (`rt`, `sync`, `macros`, `time`, …). This avoids accidentally
inheriting `full` into a small library via `{ workspace = true }`.

`uuid` likewise leaves features to the consumer — the workspace pin
covers the version, the per-crate features cover what each consumer
actually needs (typically `v4`, `v7`, or `serde`).

---

## Allowed tier

Single-consumer crates. Pinned here; commented entries in
`Cargo.toml` so a member crate adopting one only needs to uncomment
the line and reference `{ workspace = true }`.

When a second first-party consumer adopts an allowed-tier crate, the
crate gets promoted to required tier via a PR to this repo (move the
line above the fence in `Cargo.toml`, move the row up in this
table).

| Crate | Pin | Workspace features | Notes |
|---|---|---|---|
| `cpal` | `0.15` | — | audio I/O |
| `rodio` | `0.19` | — | playback over cpal |
| `hound` | `3.5` | — | WAV write |
| `lofty` | `0.22` | — | tag/metadata read |
| `rusty_link` | `=0.4.8` | — | Ableton Link FFI; pinned per upstream |
| `rtrb` | `0.3` | — | SPSC ring (audio thread) |
| `arc-swap` | `1` | — | lock-free pointer |
| `crossbeam-channel` | `0.5` | — | sync MPMC; right tool for sync TUI/rayon engines |
| `rand_distr` | matching `rand 0.10` | — | distributions |
| `rand_pcg` | `0.10` | — | deterministic PCG |
| `spin_sleep` | `1` | — | RT sleep |
| `toml` | `0.8` | — | config parsing |
| `schemars` | `1` | — | JsonSchema derive |
| `tokio-stream` | `0.1` | — | `wrappers::ReceiverStream`, unique value over futures |
| `crossterm` | `0.28` | `event-stream` | TUI input |
| `ratatui` | `0.29` | `crossterm` | TUI |
| `globset` | `0.4` | — | glob matching |
| `regex` | `1` | — | text patterns |
| `nix` | `0.31` | `signal`, `process` | signals |
| `mimalloc` | `0.1` | — | allocator |
| `rayon` | `1` | — | data-parallel iteration |
| `mlua` | `0.10` | `lua54`, `vendored` | Lua scripting |
| `rusqlite` | `0.33` | `bundled`, `modern_sqlite`, `functions` | SQLite |
| `zstd` | `0.13` | — | compression |
| `ctrlc` | `3` | — | SIGINT in CLI binaries |
| `rig-core` | `0.35` | `rmcp` | LLM/agent |
| `criterion` (dev) | `0.5` | `html_reports` | benchmarks |
| `proptest-state-machine` (dev) | `0.3` | — | proptest extension |

---

## Blacklist

`[[bans.deny]]` in `deny.toml`. Enforced by `cargo deny check`.

| Crate | Exemption | Rationale |
|---|---|---|
| `anyhow` | `wrappers = ["riffgrep"]` | Libraries must use `thiserror`. Binary crates that genuinely need anyhow add themselves to the wrapper list via PR here. |
| `clap` | none | `bpaf` won. Currently zero first-party clap usage; preventive. |
| `dasp-sample` | none (transitive via cpal still allowed) | Keeps `Sample`/`ToSample`/`FromSample` out of first-party public APIs. The future shared audio crate hand-rolls its sample/frame types in the connections style (typed quantities, f32-canonical). |
| `async-trait` | none | Workspace MSRV is Rust 1.85, which has native `async fn in trait`. Use `-> impl Future<Output = ...> + Send` where Send bounds are required. |

The existing `[bans] multiple-versions = "warn"` policy in
`deny.toml` is the secondary signal — it surfaces accidental version
drift even when the offending crate isn't on the blacklist.
