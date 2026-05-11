# PR #28 - Review Fixups and Autosquash Finalization

## Summary

Adds an explicit autosquash finalization step for review rounds. Mechanical review fixes now remain as transient fixup commits by default, while review-doc mirrors are kept as separate fixups targeting the finalized-doc commit. The new finalizer autosquashes against `origin/main`, reruns the full local gates, and force-pushes the cleaned branch with lease.

The merge wrapper now refreshes the PR head and refuses to merge if the remote branch still contains `fixup!`, `amend!`, or `squash!` commits. Local review artifacts are also committed as finalized-doc fixups instead of permanent `doc:` commits.

The workflow docs, Claude command playbooks, template-sync manifest, and Python regression suite were updated to cover the new finalization path.
