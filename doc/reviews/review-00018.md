# PR #18 — [codex] Port template workflow tooling

<!-- gh-id: 3179543341 -->
### Copilot on [`scripts/check_layers.sh`](https://github.com/cmk/template-rust/pull/18#discussion_r3179543341) (2026-05-04 05:30 UTC)

`check_layers.sh` only greps for `use ...` statements anchored at the start of the line. Any indented `use crate::...` (e.g., inside a nested `mod { ... }`) will bypass the checker, weakening the partial-order gate. Consider allowing leading whitespace in the grep (and keeping the rest of the parsing the same) so violations can’t slip through via indentation.

<!-- gh-id: 3179543365 -->
### Copilot on [`scripts/audit_run.py`](https://github.com/cmk/template-rust/pull/18#discussion_r3179543365) (2026-05-04 05:30 UTC)

The top-level docstring says `run <name>` runs an audit “unconditionally (skips early-exit gate)”, but `cmd_run` still consults `audit_report.sh since-last` and skips when nothing changed unless `--force` is passed. Please align the docstring with the actual behavior (or change the behavior to match the docs).

<!-- gh-id: 3179543373 -->
### Copilot on [`scripts/audit_run.py:106`](https://github.com/cmk/template-rust/pull/18#discussion_r3179543373) (2026-05-04 05:30 UTC)

`parse_audit()` reads markdown prompt files with `Path.read_text()` without an explicit encoding. On non-UTF-8 default locales (notably Windows), this can misdecode or fail when prompts contain Unicode punctuation (these docs already use “—”). Prefer `read_text(encoding="utf-8")` (and similarly specify UTF-8 when writing/appending the log) for deterministic behavior.

<!-- gh-id: 4217620735 -->
### copilot-pull-request-reviewer[bot] — COMMENTED ([2026-05-04 05:30 UTC](https://github.com/cmk/template-rust/pull/18#pullrequestreview-4217620735))

## Pull request overview

Ports the workflow/tooling scaffolding into `template-rust`, consolidating PR-review workflow helpers, adding recurring audit automation, and introducing a lightweight per-crate layer-import gate.

**Changes:**
- Replace review path/body shell helpers with `scripts/pr_report.py` subcommands and update workflow docs/commands accordingly.
- Add `scripts/check_layers.sh` and minimal layer-root modules for `project-core` and `project-cli`, plus hook updates to split cheap pre-commit vs expensive pre-push checks.
- Add recurring audit harness (`scripts/audit_run.py` + `scripts/audit_report.sh`) and seed audit prompt docs under `doc/audits/`.

### Reviewed changes

Copilot reviewed 42 out of 44 changed files in this pull request and generated 4 comments.

<details>
<summary>Show a summary per file</summary>

| File | Description |
| ---- | ----------- |
| scripts/workflow_state.sh | Switches review-file path probing to `scripts/pr_report.py path`. |
| scripts/review_path.sh | Removed; superseded by `scripts/pr_report.py path`. |
| scripts/pr_review.sh | Updates local-review tooling to use `pr_report.py` and renamed squash helper. |
| scripts/pr_request.sh | Usage/docs alignment for PR-number prediction helper. |
| scripts/pr_report.py | Consolidates review-path, PR-body extraction, and GitHub review mirroring into subcommands. |
| scripts/pr_reply.py | Renames/realigns reply-post helper to use `github_client`. |
| scripts/github_client.py | Renames shared GitHub CLI helper module and updates references. |
| scripts/git_squash.sh | Renames autosquash wrapper usage text to `git_squash.sh`. |
| scripts/git_merge.sh | Renames `safe_merge.sh` references to `git_merge.sh` throughout help/errors. |
| scripts/extract_pr_body.sh | Removed; superseded by `scripts/pr_report.py body`. |
| scripts/check_pii.sh | Fixes self-exclusion path to match the renamed file. |
| scripts/check_layers.sh | Adds layer import partial-order checker for workspace crates. |
| scripts/audit_run.py | Adds recurring audit runner (Codex dispatch + log append + schedule). |
| scripts/audit_report.sh | Adds early-exit state pinning for recurring audits under `.git/`. |
| doc/workflow.md | Updates workflow diagrams and references to renamed `/pr-*` commands/scripts. |
| doc/reviews/review-00000.md | Updates PR-number prediction script reference to `scripts/pr_request.sh`. |
| doc/reviews/calibration.md | Adds/renames calibration examples doc for review style prompting. |
| doc/audits/pii.md | Adds monthly PII/secrets audit prompt. |
| doc/audits/hygiene.md | Adds monthly hygiene audit prompt. |
| doc/audits/docrot.md | Adds doc-rot audit prompt (defaults to weekly cadence). |
| doc/audits/coverage.md | Adds biweekly coverage drift audit prompt. |
| doc/audits/README.md | Documents audit harness layout, prompt schema, and cron usage. |
| crates/project/src/lib.rs | Adds facade crate exposing `project::core` via optional dependency. |
| crates/project/Cargo.toml | Defines the new `project` facade crate and `core` feature wiring. |
| crates/core/src/testing.rs | Converts to compatibility re-export from `crate::test::testing`. |
| crates/core/src/test/testing.rs | Moves shared test utilities into `test` layer module. |
| crates/core/src/test/arb.rs | Adds placeholder module for shared proptest strategies under `test` layer. |
| crates/core/src/test.rs | Adds layer-root module with `//! layer:` / `//! depends-on:` sentinels. |
| crates/core/src/lib.rs | Adds `conn` and `test` module roots to support layer checking. |
| crates/core/src/conn.rs | Adds `conn` layer-root module with sentinels. |
| crates/core/src/arb.rs | Keeps `arb` as compat module pointing to `crate::test::arb`. |
| crates/cli/src/parse.rs | Adds `parse` layer-root module with sentinels. |
| crates/cli/src/main.rs | Refactors to call `command::run()` and introduces module structure. |
| crates/cli/src/command.rs | Adds `command` layer-root module depending on `parse`. |
| Cargo.toml | Adds `crates/project` to workspace and exposes `project` as a workspace dependency. |
| Cargo.lock | Adds lock entry for the new `project` crate. |
| AGENTS.md | Updates workflow/tooling references, hook model, and documents layer DAG conventions. |
| .githooks/pre-push | Adds expensive push-time gate (workspace test + clippy). |
| .githooks/pre-commit | Reduces to cheap commit-time checks (fmt + PII + layer check) with step logging. |
| .claude/settings.json | Aligns agent-side pre-commit checks to cheap commit-time set. |
| .claude/commands/pr-watch.md | Renames `/watch-pr` workflow to `/pr-watch` and updates script references. |
| .claude/commands/pr-review.md | Renames local review command and updates script/doc references. |
| .claude/commands/pr-report.md | Renames `/pull-reviews` to `/pr-report` and updates script references. |
| .claude/commands/pr-reply.md | Renames `/reply-reviews` to `/pr-reply` and updates script references. |
</details>



<details>
<summary>Comments suppressed due to low confidence (1)</summary>

**.claude/commands/pr-reply.md:3**
* The command front-matter description has two issues: (1) it says `via pr_report.py reviews` but the actual invocation elsewhere is `scripts/pr_report.py reviews` (without `scripts/` this won’t run from the repo root), and (2) “bisect-bisecting” reads like a typo and is hard to parse. Please adjust the wording so the metadata is accurate and clear.
</details>



<!-- gh-id: 3179543385 -->
### Copilot on [`scripts/audit_run.py`](https://github.com/cmk/template-rust/pull/18#discussion_r3179543385) (2026-05-04 05:30 UTC)

`append_to_log()` opens `doc/audits/log.md` without an explicit encoding. To avoid platform-dependent defaults and to match the UTF-8 audit prompt files, open the log with `encoding="utf-8"` (and ideally use UTF-8 consistently for all audit I/O).

<!-- gh-id: 3179565058 -->
#### ↳ cmk ([2026-05-04 05:39 UTC](https://github.com/cmk/template-rust/pull/18#discussion_r3179565058))

Fixed in 2507ee9 by allowing leading whitespace in the grep pattern while keeping the rest of the import parsing unchanged. Verified with scripts/check_layers.sh plus the pre-commit/pre-push gates.

<!-- gh-id: 3179565060 -->
#### ↳ cmk ([2026-05-04 05:39 UTC](https://github.com/cmk/template-rust/pull/18#discussion_r3179565060))

Fixed in 2507ee9 by opening doc/audits/log.md with encoding="utf-8", matching the UTF-8 audit prompt reads.

<!-- gh-id: 3179565095 -->
#### ↳ cmk ([2026-05-04 05:39 UTC](https://github.com/cmk/template-rust/pull/18#discussion_r3179565095))

Fixed in 2507ee9 by aligning the top-level docstring with the actual behavior: run <name> honors the early-exit gate unless --force is passed.

<!-- gh-id: 3179582215 -->
### Copilot on [`scripts/check_layers.sh:145`](https://github.com/cmk/template-rust/pull/18#discussion_r3179582215) (2026-05-04 05:46 UTC)

`emit_import_tops()` only extracts tops from single-line `use ...::{...}` forms that have the closing `}` on the same line. A common rustfmt style like `use crate::{\n    conn::X,\n    test::Y,\n};` will match the grep but yield zero extracted tops, letting cross-layer imports bypass the checker. Consider either (a) treating `use ...::{` without a same-line `}` as an explicit failure with a clear message, or (b) implementing minimal multi-line `use` collection before parsing.

<!-- gh-id: 3179582237 -->
### Copilot on [`scripts/check_layers.sh`](https://github.com/cmk/template-rust/pull/18#discussion_r3179582237) (2026-05-04 05:46 UTC)

`known_layer()` and `authorised_layer()` are identical implementations. This duplication makes future edits error-prone (fixes may land in one but not the other). Consider dropping one function and using a single helper for both checks.

<!-- gh-id: 4217663699 -->
### copilot-pull-request-reviewer[bot] — COMMENTED ([2026-05-04 05:46 UTC](https://github.com/cmk/template-rust/pull/18#pullrequestreview-4217663699))

## Pull request overview

Copilot reviewed 42 out of 44 changed files in this pull request and generated 3 comments.


<details>
<summary>Comments suppressed due to low confidence (2)</summary>

**scripts/pr_review.sh:14**
* `--check` currently runs `scripts/pr_report.py path` without a PR number, which in turn calls `scripts/pr_request.sh` and may invoke `gh`/network access. That makes the cheap capability check slower and can fail in unauthenticated/offline environments. Prefer passing an explicit dummy PR number (so it’s purely local) or adding a `--no-gh`/`--local-only` path mode for checks.
**scripts/pr_report.py:57**
* `review_path()` defaults to a relative `Path("doc/reviews")`, so `path/body/reviews` behavior depends on the current working directory. If someone runs `scripts/pr_report.py` outside the repo root, it can print/write review files into the wrong place. Consider anchoring defaults to the repo root (e.g., derive `REPO_ROOT` from `__file__` or `git rev-parse`) and only using relative paths for display.
</details>



<!-- gh-id: 3179582252 -->
### Copilot on [`crates/core/src/test/arb.rs`](https://github.com/cmk/template-rust/pull/18#discussion_r3179582252) (2026-05-04 05:46 UTC)

The module docs say to `use project_core::arb;`, but the actual strategies live under `project_core::test::arb` (and `project_core::arb` is currently just a compatibility stub). Either update the docs here to point at `project_core::test::arb` or re-export the relevant items from `project_core::arb` so the documented import works.


<!-- gh-id: 3179607310 -->
#### ↳ cmk ([2026-05-04 05:56 UTC](https://github.com/cmk/template-rust/pull/18#discussion_r3179607310))

Fixed in c050774 by adding minimal multiline import collection before parsing. The checker now joins rustfmt-style grouped imports like use crate::{ conn::X, test::Y }; and verifies the same top-level layer names instead of missing them. Verified with bash -n scripts/check_layers.sh, scripts/check_layers.sh, and the pre-push test/clippy gate.

<!-- gh-id: 3179607482 -->
#### ↳ cmk ([2026-05-04 05:56 UTC](https://github.com/cmk/template-rust/pull/18#discussion_r3179607482))

Fixed in 93eaa18 by replacing the duplicate known_layer/authorised_layer helpers with a single layer_in_list helper used for both checks.

<!-- gh-id: 3179650885 -->
### Copilot on [`scripts/check_layers.sh:81`](https://github.com/cmk/template-rust/pull/18#discussion_r3179650885) (2026-05-04 06:09 UTC)

`check_layers.sh` can be bypassed by importing layer modules via a crate’s own extern name (e.g., `use project_cli::parse::...`) because `use_re` only matches `crate|project|project_core`. Since Rust puts the crate name in the extern prelude, this means cross-layer imports in `project-cli` won’t be caught if written as `project_cli::...`. Consider including each crate’s own name (hyphen→underscore) in the matcher for that crate (or generating the prefixes from Cargo metadata) so the gate can’t be sidestepped by path style.

<!-- gh-id: 3179650901 -->
### Copilot on [`AGENTS.md`](https://github.com/cmk/template-rust/pull/18#discussion_r3179650901) (2026-05-04 06:09 UTC)

The layering rule prose says `check_layers.sh` fails on `use project::<top>`, but the new facade crate exposes layers under `project::core::...` (and `check_layers.sh` currently only extracts the segment immediately after `project::`, i.e., it would see `core`, not `conn/test`). Either adjust the rule text to reflect what’s actually checked, or extend the checker to understand `project::core::<layer>` so the documented bypass-avoidance remains true.


<!-- gh-id: 4217743179 -->
### copilot-pull-request-reviewer[bot] — COMMENTED ([2026-05-04 06:09 UTC](https://github.com/cmk/template-rust/pull/18#pullrequestreview-4217743179))

## Pull request overview

Copilot reviewed 42 out of 44 changed files in this pull request and generated 4 comments.


<details>
<summary>Comments suppressed due to low confidence (1)</summary>

**scripts/pr_report.py:271**
* `pr_report.py path` currently prints an absolute filesystem path (because `DEFAULT_REVIEW_DIR` is absolute), but the docstring says it prints `doc/reviews/review-NNNNN.md`. This mismatch can make docs/commands that embed the output noisier and may break tooling that expects a repo-relative path. Consider printing the path relative to `REPO_ROOT` (or update the docstring/consumers to explicitly expect absolute paths).
</details>



<!-- gh-id: 3179650912 -->
### Copilot on [`crates/project/src/lib.rs`](https://github.com/cmk/template-rust/pull/18#discussion_r3179650912) (2026-05-04 06:09 UTC)

This compile-smoke test passes "." as the manifest dir to `fixture_or_skip`, which makes the behavior depend on the test process’s current working directory. Using `env!("CARGO_MANIFEST_DIR")` (or otherwise passing an explicit crate root path) keeps the test stable if the workspace adds a top-level `tests/` directory or if the runner’s CWD changes.


<!-- gh-id: 3179650926 -->
### Copilot on [`doc/workflow.md:114`](https://github.com/cmk/template-rust/pull/18#discussion_r3179650926) (2026-05-04 06:09 UTC)

`doc/workflow.md` says the `/pr-watch` loop stores counters under `.pr-watch/…` and that it’s gitignored, but the repo’s `.gitignore` currently ignores `/.watch-pr/` (old name) and does not ignore `/.pr-watch/`. As-is, running `/pr-watch` will create untracked files that show up in `git status`. Add `/.pr-watch/` to `.gitignore` (or update the workflow docs to match the ignored path).


<!-- gh-id: 3179661841 -->
#### ↳ cmk ([2026-05-04 06:13 UTC](https://github.com/cmk/template-rust/pull/18#discussion_r3179661841))

Fixed in 210d103 by making check_layers.sh use per-crate import roots. project-cli now checks crate:: and project_cli:: imports, and project-core checks crate::, project_core::, and project::core:: imports. Verified with bash -n scripts/check_layers.sh, scripts/check_layers.sh, and the pre-push test/clippy gate.

<!-- gh-id: 3179661885 -->
#### ↳ cmk ([2026-05-04 06:13 UTC](https://github.com/cmk/template-rust/pull/18#discussion_r3179661885))

Fixed in 210d103 by passing env!("CARGO_MANIFEST_DIR") to fixture_or_skip instead of relying on the test process current working directory. cargo test --workspace passed afterward.

<!-- gh-id: 3179661900 -->
#### ↳ cmk ([2026-05-04 06:13 UTC](https://github.com/cmk/template-rust/pull/18#discussion_r3179661900))

Fixed in 210d103 by extending the checker to understand project::core::<layer> facade paths and updating AGENTS.md to describe the actual checked import forms.

<!-- gh-id: 3179662030 -->
#### ↳ cmk ([2026-05-04 06:13 UTC](https://github.com/cmk/template-rust/pull/18#discussion_r3179662030))

Fixed in 210d103 by updating .gitignore from the old /.watch-pr/ path to /.pr-watch/, matching doc/workflow.md and the renamed /pr-watch command.
