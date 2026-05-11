# PR #29 - Review Fixups and Autosquash Finalization

## Summary

Adds an explicit autosquash finalization step for review rounds. Mechanical review fixes now remain as transient fixup commits by default, while review-doc mirrors are kept as separate fixups targeting the finalized-doc commit. The new finalizer autosquashes against `origin/main`, reruns the full local gates, and force-pushes the cleaned branch with lease.

The merge wrapper now refreshes the PR head and refuses to merge if the remote branch still contains `fixup!`, `amend!`, or `squash!` commits. Local review artifacts are also committed as finalized-doc fixups instead of permanent `doc:` commits.

The workflow docs, Claude command playbooks, template-sync manifest, and Python regression suite were updated to cover the new finalization path.

## Local review (2026-05-11)

**Branch:** plan/2026-05-11-01
**Commits:** 3 (origin/main..plan/2026-05-11-01)
**Reviewer:** Codex (`codex review --base origin/main`)
**Prompt fingerprint:** AGENTS.md=e1ce4afc1e17d25b5719cf76a0bd080d57b53b36 calibration=da4563c5de79900526f1af39c38320bea4cee6c5

---

The changes consistently update the workflow to use transient fixup commits, add a final autosquash gate, and extend merge protection. The new scripts and tests cover the main intended paths, and I did not find a discrete introduced bug that would block correctness.

<!-- gh-id: 3216939002 -->
### Copilot on [`scripts/pr_review.sh:134`](https://github.com/cmk/template-rust/pull/29#discussion_r3216939002) (2026-05-11 07:13 UTC)

`doc_commit` is derived via `git log -n 1 -- <review_file>`, which returns the most recent commit that touched the review file. After the first local-review fixup, subsequent runs will likely target the previous fixup commit instead of the original finalized-doc commit, producing nested `fixup! fixup! ...` subjects and diverging from the stated policy of targeting the finalized-doc commit. Consider resolving the finalized-doc commit explicitly (e.g., the commit that *introduced* the review file via `--diff-filter=A`, or otherwise identifying the original finalize-doc commit) and always using that SHA as the fixup target.

<!-- gh-id: 4261391495 -->
### copilot-pull-request-reviewer[bot] — COMMENTED ([2026-05-11 07:13 UTC](https://github.com/cmk/template-rust/pull/29#pullrequestreview-4261391495))

## Pull request overview

Introduces an explicit “autosquash finalization” step in the review/merge workflow: review-round mechanical fixes remain as transient `fixup!/amend!/squash!` commits during iteration, then a new finalizer script autosquashes against `origin/main`, reruns full local gates, and force-pushes the cleaned PR head. Merge is additionally guarded to refuse PR heads that still contain autosquashable commits.

**Changes:**
- Add `scripts/git_autosquash_finalize.sh` to autosquash PR branches, rerun gates, and force-push with lease.
- Extend `scripts/git_merge.sh` to refresh refs and refuse merges when the remote PR head still contains autosquashable commits.
- Update local-review behavior/docs and add Python regression tests + template-sync manifest entries for the new workflow.

### Reviewed changes

Copilot reviewed 16 out of 16 changed files in this pull request and generated 2 comments.

<details>
<summary>Show a summary per file</summary>

| File | Description |
| ---- | ----------- |
| `tests/test_template_sync.py` | Asserts the template-sync manifest includes the new finalizer + regression tests. |
| `tests/test_pr_review.py` | Updates regression test to expect local review artifacts committed as a doc fixup. |
| `tests/test_git_merge.py` | Adds regression test that merge guard rejects remote fixup commits and blocks `gh pr merge`. |
| `tests/test_git_autosquash_finalize.py` | Adds regression test covering autosquash, gate execution, and force-push behavior. |
| `scripts/template_sync.sh` | Adds new workflow files/tests to the VERBATIM manifest. |
| `scripts/pr_review.sh` | Switches local-review artifact commit from `doc:` to `--fixup` targeting the finalized-doc commit. |
| `scripts/git_merge.sh` | Fetches `origin/main`, fetches PR head, and blocks merge if autosquashable commits exist remotely. |
| `scripts/git_autosquash_finalize.sh` | New script to autosquash against `origin/main`, rerun gates, and force-push with lease. |
| `doc/workflow.md` | Updates FSM and narrative to include `autosquash_finalized` as a pre-merge requirement. |
| `doc/reviews/review-00028.md` | Review record for this PR. |
| `doc/plans/plan-2026-05-11-01.md` | Plan describing the new workflow and verification properties. |
| `AGENTS.md` | Updates workflow policy: mechanical fixes as fixups; require finalization before merge. |
| `.claude/commands/pr-watch.md` | Updates playbook to push transient fixups and require finalization before merge. |
| `.claude/commands/pr-review.md` | Updates playbook to keep fixups during review and commit local review as doc fixup. |
| `.claude/commands/pr-report.md` | Updates guidance: review-doc changes ride as doc fixups rather than permanent `doc:` commits. |
| `.claude/commands/pr-reply.md` | Updates playbook to create transient fixup commits (impl + doc) and push them together. |
</details>






<!-- gh-id: 3216939027 -->
### Copilot on [`doc/plans/plan-2026-05-11-01.md:46`](https://github.com/cmk/template-rust/pull/29#discussion_r3216939027) (2026-05-11 07:13 UTC)

The plan’s “Drift caught” bullet cites specific file line numbers (e.g. `pr-review.md:105`, `pr-reply.md:134`, `pr-watch.md:115`) that don’t match the current locations of the updated gardener-rule anchors in this PR. Since these references are meant to be actionable, either update them to the correct current line numbers or remove the line numbers to avoid stale/misleading pointers.

