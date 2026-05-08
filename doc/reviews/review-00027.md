# PR #27 — `scripts/template_sync.sh`: pull-mode drift check across downstream repos

## Summary

Adds `scripts/template_sync.sh` so a maintainer can detect (and
optionally apply) drift between this template and downstream repos
seeded from it, without manually diffing each path.

### What changed

- `scripts/template_sync.sh` (new). Manifest-driven sync between
  template-rust and downstream forks. Two arrays at the top of the
  script:
  - `VERBATIM_PATHS` — files where downstream must match template-rust
    byte-for-byte (workflow scripts under `scripts/`, the two git
    hooks, the four `.claude/commands/*.md`, audit prose under
    `doc/audits/`, `doc/reviews/calibration.md`, `doc/workflow.md`,
    and the Python regression suite under `tests/`).
  - `SURGICAL_PATHS` — files that always differ per project
    (`AGENTS.md`, `Cargo.toml`, `rust-toolchain.toml`, `rustfmt.toml`,
    `deny.toml`, `.github/workflows/ci.yml`). Reported but never
    auto-copied.
- Default mode is read-only drift: report `match` / `drift` / `missing`
  for verbatim, `match` / `differs` for surgical. Exit 1 if any
  verbatim path drifted or is missing — CI-friendly.
- `--apply` mode copies the verbatim subset using `install -m` so
  githook executable bits survive. Refuses a dirty downstream tree;
  surgical paths are explicitly skipped with a one-line note.
- Refusal guards: not in template-rust working tree, non-git
  downstream argument, dirty downstream under `--apply`, duplicate
  downstream argument, or downstream pointing at template-rust itself.
- Downstream paths are positional CLI arguments; no repo names are
  encoded in the script.
- `tests/test_template_sync.py` (new). Nine cases covering pristine
  match, drift, missing-file, `--apply` happy-path, dirty refusal,
  non-git refusal, duplicate-arg refusal, self-sync refusal, and
  no-args usage. Parses the manifest out of the script with a regex
  so adding a verbatim/surgical path doesn't require editing
  fixtures.
- `AGENTS.md` (modified). New "Syncing downstream forks" section near
  the top with the surgical-path list and a typical invocation.
- `doc/audits/README.md` (modified). One-paragraph "See also" footer
  pointing at the new script.

### Verification

- `bash -n scripts/template_sync.sh`: clean.
- `python3 -m unittest`: 22 passed (9 new for `test_template_sync`).
- `cargo test --workspace`: green.
- `cargo clippy --all-targets -- -D warnings`: green.
- `cargo fmt --all -- --check`: green.
- `scripts/template_sync.sh ../adat`: reports drift on adat's
  pre-batch `check_pii.sh`, the local-extension `check_layers.sh`,
  and the older `git_merge.sh` — exit 1 as designed.

### Deferred

- **Local-extension manifest tier.** A future third tier
  (`LOCAL_EXTENSION_PATHS`) for paths where downstream may diverge
  intentionally — the immediate need is `scripts/check_layers.sh`
  for adat (extra crate roots + `#[cfg(test)]` cutoff). Without it,
  adat's sync will always report `check_layers.sh: drift`.
- **`--apply --force`** for dirty downstreams.
- **Externalized manifest** (e.g. `template_sync.toml`).
- **Auto-commit / auto-PR**. Out of scope by design — pull model only.

## Local review (2026-05-08)

**Branch:** plan/2026-05-08-03
**Commits:** 3 (origin/main..plan/2026-05-08-03)
**Reviewer:** Codex (`codex review --base origin/main`)
**Prompt fingerprint:** AGENTS.md=02d75717d4a011a259975a8871afb571ef13ccc8 calibration=da4563c5de79900526f1af39c38320bea4cee6c5

---

The new --apply path is not portable to the Ubuntu CI environment and will fail when copying drifted files. The manifest also omits the newly added sync artifacts, so downstream repos cannot be fully brought up to date by the tool.

Full review comments:

- [P1] Use a portable mode lookup before install — scripts/template_sync.sh:237-237
  On Ubuntu/GNU coreutils, including this repo's CI runner, `stat -f` does not take a format argument; it treats `'%Lp'` as a filename and can still print filesystem information for `$src` before the fallback `stat -c` runs. For any `--apply` that copies a drifted file, `install -m "$(...)"` receives a multi-line/non-octal mode and fails, which also breaks the new unittest apply case in CI; the identical expression in the missing-file branch needs the same fix.

- [P2] Add new sync artifacts to the manifest — scripts/template_sync.sh:50-50
  `--apply` only copies paths listed in `VERBATIM_PATHS`, but this PR adds `scripts/template_sync.sh` and `tests/test_template_sync.py` without listing either one. A downstream updated with the new tool will therefore still be missing the sync tool and its regression test, even though the docs describe the `scripts/` tooling and Python regression suite as canonical downstream-owned files.

