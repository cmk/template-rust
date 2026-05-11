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
