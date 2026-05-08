---
applyTo: "doc/**/*.md"
---

# Documentation review style

These instructions apply to any markdown file under `doc/` — design
sketches, plans, review records, session notes, reference material.
They narrow Copilot's review voice for prose content. Source code
under `crates/` is reviewed under the default (strict) voice; nothing
here relaxes that.

## Scope exclusion: `doc/reviews/review-*.md`

These files are an audit trail. They accumulate the verdict from
codex (Tier 1 local review), the GitHub Copilot review (Tier 2
post-push), human review comments, and reply mirrors — the discussion
*about* the PR, not the PR's own work product. Commenting on the
audit trail is noise: it's a record of decisions already made, not a
doc that asks for review.

**If the file matches `doc/reviews/review-*.md` (e.g.
`review-00017.md`): surface zero findings.** Skip every check below.
Return without comment.

(`doc/reviews/calibration.md`, `doc/reviews/review-00000.md` and any
future non-`review-NNNNN.md` file in `doc/reviews/` remain in scope
under the rules below — they are working docs, not the audit trail.)

## What to flag

The bar for surfacing a finding on a `doc/` markdown file is high.
A finding must do at least one of:

  1. **Identify a factual error a reader would otherwise act on.**
     A wrong formula, a claim about the code that doesn't match what
     the code does, a line-number reference that points at the wrong
     site, a broken cross-link to a real file.
  2. **Resolve an ambiguity that could mislead a reader on
     non-trivial subject matter.** Units missing on a quantity (`SNR`
     without saying whether it's in dB or linear), an identifier
     defined two ways, a statement that could be read two ways where
     only one is correct.
  3. **Catch a contradiction within the PR.** A code snippet that
     disagrees with the prose directly above or below it; a summary
     table whose values don't match the per-row detail tables. A PR
     that breaks an established convention in the file it touches
     (the convention is the contract; breaking it is a contradiction).
  4. **Catch stale content the PR claims to update but didn't.** A
     catalog whose top-level summary still lists an item the PR
     removed. A doc-comment edit that misses the matching ToC entry.
  5. **Plan §Review / Retrospective / Conclusion claims that explain
     away a relaxation.** When reviewing files under `doc/plans/`,
     the author's retro section is the highest-value ratification
     trap. Treat sentences like "all N tests pass under this shape",
     "tolerated via monotone-with-equality", "the test rename is
     fine because…", "the deferred case is structural and doesn't
     matter" as **bullshit until proven otherwise**. Verify every
     relaxation claim against the type / API the PR diff still ships:

       - Was the type declaration weakened to match the relaxation?
         If not, escalate `must-fix` — soundness gap, not test
         deviation.
       - Does "all N proptests pass" mean coverage of the original
         contract, or of a renamed weaker predicate? If the latter,
         name the gap.
       - Does a "deferred for follow-up" line correspond to a tracked
         issue or just a sentence the author hopes the reviewer will
         nod at?

If a finding does none of these, **do not surface it**. Default to
surfacing nothing.

## What to skip

- **Single-word style preferences.** British vs American spelling
  variants where both are standard English (`parameterise` /
  `parameterize`, `behaviour` / `behavior`). The author's choice
  stands.
- **Punctuation, spacing, and formatting preferences** that don't
  change the meaning. `±5 s` vs `0 to -5 s`, hyphenated vs
  unhyphenated compound, en-dash vs em-dash, sentence vs title case
  in headings.
- **Comment-style nits in illustrative code snippets.** Rust snippets
  in docs are illustrations, not `use` statements a reader is expected
  to paste verbatim. A locator comment like `// my-crate::module`
  communicates the same thing as `// my_crate::module`.
- **Pre-existing patterns on unchanged lines.** If the PR touches file
  X and a pattern the reviewer would otherwise flag also appears on
  lines the PR did *not* modify, do not flag it. Those are concerns
  for a separate cleanup PR.
- **Anything that reduces to "I'd phrase this differently."** Phrasing
  belongs to the author.

## Severity

**There is no `nit:` tier.** If a finding doesn't meet the §What to
flag bar, it doesn't get surfaced — full stop. Style and punctuation
findings are out of scope.

Findings that meet the bar are **must-fix**: would cause a reader to
misunderstand the system, is demonstrably wrong on the current
codebase, contradicts the PR's own claims, or ratifies a §Review
that the diff doesn't back up.

Plan §Review skepticism findings (category 5 above) are always
must-fix even when the prose itself reads cleanly — they are
substantive findings about whether the doc is honest about the diff.

## How to batch

If a single file accumulates multiple substantive findings, combine
them into a single inline comment citing each line number, rather
than opening a separate thread per finding. The author's review-time
budget is finite — preserve it for substantive matters.

A reasonable expectation: most `doc/` PRs surface zero findings. The
default outcome of this review is silence.
