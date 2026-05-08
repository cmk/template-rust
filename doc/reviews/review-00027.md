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


<!-- gh-id: 3207888188 -->
### Copilot on [`scripts/template_sync.sh:70`](https://github.com/cmk/template-rust/pull/27#discussion_r3207888188) (2026-05-08 09:56 UTC)

`VERBATIM_PATHS` lists several `doc/audits/*.md` files but omits `doc/audits/coverage.md`, even though it exists and is part of the audit suite layout (`doc/audits/README.md` lists it). As a result, drift on `coverage.md` won’t be detected or applied. Add it to `VERBATIM_PATHS` (or explicitly document why it’s intentionally excluded).


<!-- gh-id: 3207888221 -->
### Copilot on [`scripts/template_sync.sh:144`](https://github.com/cmk/template-rust/pull/27#discussion_r3207888221) (2026-05-08 09:56 UTC)

The “must run from the template-rust working tree” guard doesn’t actually detect a stale copy/symlinked copy living inside a downstream repo: if `template_sync.sh` exists inside some other git repo, `template_root` will be that repo’s toplevel and this check will pass, causing the script to treat the downstream as the template source-of-truth. Consider adding a template-only marker file (not synced) and refusing when it’s absent, or resolving the script’s real path and validating it lives in the expected template repo.

<!-- gh-id: 3207888234 -->
### Copilot on [`scripts/template_sync.sh:218`](https://github.com/cmk/template-rust/pull/27#discussion_r3207888234) (2026-05-08 09:56 UTC)

When a manifest entry is missing in the template (`[ ! -e "$src" ]`), the script only prints a SKIP to stderr and continues. That can make the overall run exit 0 even though the manifest/template are inconsistent, and downstreams won’t be updated for that path. Treat a missing template source as an error (exit 2) or at least set a non-zero overall status so CI can catch it.


<!-- gh-id: 3207888254 -->
### Copilot on [`tests/test_template_sync.py:63`](https://github.com/cmk/template-rust/pull/27#discussion_r3207888254) (2026-05-08 09:56 UTC)

The tests exercise `--apply` copying content, but they don’t validate the advertised behavior of preserving executable bits (notably for `.githooks/pre-commit` / `.githooks/pre-push`). Consider setting an executable mode on one of the hook files in `_make_template()` and asserting that after `--apply` the downstream file has the same executable bit set.

<!-- gh-id: 3207888274 -->
### Copilot on [`tests/test_template_sync.py:54`](https://github.com/cmk/template-rust/pull/27#discussion_r3207888274) (2026-05-08 09:56 UTC)

The comment says `_make_template` overwrites “the script itself, and its regression test” with real content, but the code only overwrites `scripts/template_sync.sh` (the `tests/test_template_sync.py` stub remains). Either update the comment or also write the real test content so the fixture matches the comment.


<!-- gh-id: 3207888294 -->
### Copilot on [`doc/plans/plan-2026-05-08-03.md:283`](https://github.com/cmk/template-rust/pull/27#discussion_r3207888294) (2026-05-08 09:56 UTC)

This plan doc diverges from the code shipped in this PR:
- T1’s “Initial set” list for `VERBATIM_PATHS` omits at least `scripts/template_sync.sh` and `tests/test_template_sync.py`, even though the script’s manifest includes them.
- The Review section claims the “must run from template-rust” guard catches invocation from a stale copy inside a downstream repo, but the current implementation only checks that the script lives under *a* git toplevel, so a downstream copy would still pass.
- “T5 covers all nine cases … plus a no-args usage check” is internally inconsistent with the actual test suite (the no-args check is one of the nine).
Please update the plan text so it matches the actual manifest/behavior/tests.

<!-- gh-id: 4251344760 -->
### copilot-pull-request-reviewer[bot] — COMMENTED ([2026-05-08 09:56 UTC](https://github.com/cmk/template-rust/pull/27#pullrequestreview-4251344760))

## Pull request overview

Adds a new maintainer-facing sync tool to detect (and optionally apply) drift between this template repo and downstream repos seeded from it, plus regression tests and documentation updates to support the workflow.

**Changes:**
- Added `scripts/template_sync.sh` to report verbatim vs surgical drift across one or more downstream git working trees, with an optional `--apply` mode for verbatim paths.
- Added `tests/test_template_sync.py` unittest coverage for key drift/refusal/apply scenarios.
- Updated workflow documentation (`AGENTS.md`, `doc/audits/README.md`) and added planning/review records under `doc/`.

### Reviewed changes

Copilot reviewed 6 out of 6 changed files in this pull request and generated 7 comments.

<details>
<summary>Show a summary per file</summary>

| File | Description |
| ---- | ----------- |
| `scripts/template_sync.sh` | New manifest-driven drift checker / optional applier for canonical template-owned paths. |
| `tests/test_template_sync.py` | New unittests exercising drift detection, refusal guards, and `--apply` behavior. |
| `AGENTS.md` | Documents how maintainers should run the sync tool and what remains surgical. |
| `doc/audits/README.md` | Adds a cross-reference to the new cross-repo drift tool. |
| `doc/plans/plan-2026-05-08-03.md` | Plan/design write-up for the feature and its intended behavior. |
| `doc/reviews/review-00027.md` | Review record for the PR. |
</details>






<!-- gh-id: 3207888320 -->
### Copilot on [`AGENTS.md:42`](https://github.com/cmk/template-rust/pull/27#discussion_r3207888320) (2026-05-08 09:56 UTC)

The doc says the surgical set reports only “match / differs”, but the script also emits a distinct “missing downstream (surgical — not auto-copied)” status when a surgical path is absent. Update this description to include the missing case (or clarify that “missing” is treated as “differs” in the summary).


<!-- gh-id: 3207910731 -->
#### ↳ cmk ([2026-05-08 10:01 UTC](https://github.com/cmk/template-rust/pull/27#discussion_r3207910731))

Fixed — added doc/audits/coverage.md to VERBATIM_PATHS.

<!-- gh-id: 3207911502 -->
#### ↳ cmk ([2026-05-08 10:01 UTC](https://github.com/cmk/template-rust/pull/27#discussion_r3207911502))

Fixed — added a `.template-rust-root` marker file at the template root, intentionally excluded from VERBATIM_PATHS / SURGICAL_PATHS so downstream repos never receive a copy. The script now refuses with exit 2 if the marker is missing, which catches stale-copy invocations from inside a downstream repo.

<!-- gh-id: 3207912382 -->
#### ↳ cmk ([2026-05-08 10:01 UTC](https://github.com/cmk/template-rust/pull/27#discussion_r3207912382))

Fixed — missing template source is now an error (exit 2) for both VERBATIM and SURGICAL paths, with a message naming the offending path. Manifest/template inconsistency aborts the run rather than silently skipping.

<!-- gh-id: 3207913230 -->
#### ↳ cmk ([2026-05-08 10:01 UTC](https://github.com/cmk/template-rust/pull/27#discussion_r3207913230))

Fixed — added test_apply_preserves_exec_bit_on_hook: marks .githooks/pre-commit executable in the template fixture, drifts content+mode in the downstream, runs --apply, and asserts the resulting mode matches template (S_IXUSR set).

<!-- gh-id: 3207914055 -->
#### ↳ cmk ([2026-05-08 10:01 UTC](https://github.com/cmk/template-rust/pull/27#discussion_r3207914055))

Fixed — updated the comment in _make_template to accurately say the script's stub is overwritten with real content, while the regression test stub stays as a stub (it's not executed by the script under test).

<!-- gh-id: 3207914907 -->
#### ↳ cmk ([2026-05-08 10:02 UTC](https://github.com/cmk/template-rust/pull/27#discussion_r3207914907))

Fixed — plan T1's Initial Set list now includes scripts/template_sync.sh, tests/test_template_sync.py, and doc/audits/coverage.md to match the shipped manifest. The Review section's "stale-copy guard" claim is rewritten to describe the actual two-step guard (git-toplevel check + .template-rust-root marker). The "nine plus a no-args check" wording is corrected to "ten cases (the nine listed plus an exec-bit preservation test)" — the no-args case is one of the original nine.

<!-- gh-id: 3207915626 -->
#### ↳ cmk ([2026-05-08 10:02 UTC](https://github.com/cmk/template-rust/pull/27#discussion_r3207915626))

Fixed — AGENTS.md now reads 'match / drift / missing for the verbatim set, and match / differs / missing for the surgical set' to match the script's actual surgical-path output.

<!-- gh-id: 3207943854 -->
### Copilot on [`scripts/template_sync.sh:153`](https://github.com/cmk/template-rust/pull/27#discussion_r3207943854) (2026-05-08 10:07 UTC)

The template-root validation only checks that `template_root` is a git toplevel. If this script is invoked from a copied/symlinked version that lives inside a downstream repo, this check can still pass and `--apply` would copy from the wrong (stale) source tree. Add a template-only marker file at the real template root (intentionally *not* synced) and refuse to run if it’s missing, or otherwise validate the script’s realpath belongs to the expected template repo.

<!-- gh-id: 3207943893 -->
### Copilot on [`scripts/template_sync.sh:218`](https://github.com/cmk/template-rust/pull/27#discussion_r3207943893) (2026-05-08 10:07 UTC)

When a manifest entry is missing in the template (`[ ! -e "$src" ]`), the script logs a SKIP and continues. That can mask a broken/obsolete manifest and still allow a 0/1 exit depending on downstream drift. Treat this as a hard error (exit 2) so CI/users don’t get a false sense of a successful sync check.


<!-- gh-id: 3207943924 -->
### Copilot on [`scripts/template_sync.sh:248`](https://github.com/cmk/template-rust/pull/27#discussion_r3207943924) (2026-05-08 10:07 UTC)

For surgical paths, a missing template source (`[ ! -e "$src" ]`) is silently ignored. This makes the manifest and template tree able to drift out of sync without being detected. Consider aborting with exit 2 here as well (consistent with verbatim handling once that’s made strict).


<!-- gh-id: 3207943954 -->
### Copilot on [`scripts/template_sync.sh:75`](https://github.com/cmk/template-rust/pull/27#discussion_r3207943954) (2026-05-08 10:07 UTC)

`doc/audits/coverage.md` exists in the repo but is not listed in `VERBATIM_PATHS`, so drift on that audit definition won’t be detected or applied. Add `doc/audits/coverage.md` to the verbatim manifest (or explicitly move it out of `doc/audits/` if it’s intentionally not canonical).

<!-- gh-id: 3207943994 -->
### Copilot on [`tests/test_template_sync.py:173`](https://github.com/cmk/template-rust/pull/27#discussion_r3207943994) (2026-05-08 10:07 UTC)

The tests cover `--apply` copying content but don’t verify the advertised behavior of preserving executable bits (especially for `.githooks/pre-commit` / `.githooks/pre-push`). Add a regression test that makes a hook executable in the template fixture, ensures the downstream differs (content and/or mode), runs `--apply`, and asserts the downstream file’s execute bit matches the template.


<!-- gh-id: 4251422813 -->
### copilot-pull-request-reviewer[bot] — COMMENTED ([2026-05-08 10:07 UTC](https://github.com/cmk/template-rust/pull/27#pullrequestreview-4251422813))

## Pull request overview

Copilot reviewed 6 out of 6 changed files in this pull request and generated 8 comments.





<!-- gh-id: 3207944020 -->
### Copilot on [`tests/test_template_sync.py:54`](https://github.com/cmk/template-rust/pull/27#discussion_r3207944020) (2026-05-08 10:07 UTC)

The comment says `_make_template` overwrites “the script itself, and its regression test” with real content, but the code only overwrites `scripts/template_sync.sh` (the test file remains a stub). Update the comment to match what the fixture actually does.


<!-- gh-id: 3207944054 -->
### Copilot on [`AGENTS.md:42`](https://github.com/cmk/template-rust/pull/27#discussion_r3207944054) (2026-05-08 10:07 UTC)

This section says the surgical set reports only “match / differs”, but the script also emits a distinct “missing downstream (surgical — not auto-copied)” status when a surgical path is absent. Update the wording to include the missing case (or clarify how missing is treated).


<!-- gh-id: 3207944095 -->
### Copilot on [`doc/plans/plan-2026-05-08-03.md:151`](https://github.com/cmk/template-rust/pull/27#discussion_r3207944095) (2026-05-08 10:07 UTC)

This plan describes surgical-path reporting in `--apply` as printing `path: SKIP (surgical merge required)`, but the current script reports surgical paths as `differs (surgical merge required)` or `missing downstream (surgical — not auto-copied)` (and does so in both modes). Update the plan text so it matches the behavior shipped in the script.


<!-- gh-id: 3207966628 -->
#### ↳ cmk ([2026-05-08 10:11 UTC](https://github.com/cmk/template-rust/pull/27#discussion_r3207966628))

Already fixed in the previous (unpushed) round commit — added a .template-rust-root marker file at the template root, intentionally excluded from VERBATIM_PATHS / SURGICAL_PATHS so downstream repos never receive a copy. The script refuses with exit 2 if the marker is missing. The commit hasn't been pushed yet, which is why this still surfaced.

<!-- gh-id: 3207967495 -->
#### ↳ cmk ([2026-05-08 10:11 UTC](https://github.com/cmk/template-rust/pull/27#discussion_r3207967495))

Already fixed in the previous (unpushed) round commit — missing template source for VERBATIM_PATHS now exits 2 with a message naming the path.

<!-- gh-id: 3207968287 -->
#### ↳ cmk ([2026-05-08 10:11 UTC](https://github.com/cmk/template-rust/pull/27#discussion_r3207968287))

Already fixed in the previous (unpushed) round commit — missing template source for SURGICAL_PATHS now also exits 2, consistent with verbatim handling.

<!-- gh-id: 3207968984 -->
#### ↳ cmk ([2026-05-08 10:12 UTC](https://github.com/cmk/template-rust/pull/27#discussion_r3207968984))

Already fixed in the previous (unpushed) round commit — added doc/audits/coverage.md to VERBATIM_PATHS (and to the plan's T1 listing).

<!-- gh-id: 3207969809 -->
#### ↳ cmk ([2026-05-08 10:12 UTC](https://github.com/cmk/template-rust/pull/27#discussion_r3207969809))

Already fixed in the previous (unpushed) round commit — test_apply_preserves_exec_bit_on_hook chmods .githooks/pre-commit executable in the template fixture, drifts content+mode in the downstream, runs --apply, and asserts S_IXUSR is set and the mode matches the template.

<!-- gh-id: 3207970444 -->
#### ↳ cmk ([2026-05-08 10:12 UTC](https://github.com/cmk/template-rust/pull/27#discussion_r3207970444))

Already fixed in the previous (unpushed) round commit — _make_template's comment now accurately says only the script stub is overwritten, not the test stub.

<!-- gh-id: 3207971108 -->
#### ↳ cmk ([2026-05-08 10:12 UTC](https://github.com/cmk/template-rust/pull/27#discussion_r3207971108))

Already fixed in the previous (unpushed) round commit — AGENTS.md now reads 'match / drift / missing for the verbatim set, and match / differs / missing for the surgical set'.

<!-- gh-id: 3207971862 -->
#### ↳ cmk ([2026-05-08 10:12 UTC](https://github.com/cmk/template-rust/pull/27#discussion_r3207971862))

Fixed — plan T3 now describes surgical reporting under --apply as 'differs (surgical merge required)' (or 'missing downstream (surgical — not auto-copied)' when absent), matching the script's actual output in both check and apply modes.
