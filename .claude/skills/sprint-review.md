---
name: sprint-review
description: >
  Review a completed sprint by comparing the plan document against the actual
  implementation diff. Use this skill whenever the user asks to review a sprint,
  review the last sprint, review recent commits against a plan, or says
  "/sprint-review". Also use it after completing a sprint on a branch before
  rebasing onto main — it's the manual quality gate in the TDD workflow.
---

# Sprint Review

You are orchestrating a code review that compares a sprint plan against its
implementation. The review is performed by an **independent agent** — not you.
Your job is to gather the inputs, launch the reviewer, and place the output.

## Step 1: Identify the plan

If the user specifies a plan (e.g., "review plan 04" or a path), use that.

Otherwise, find the most recent plan:

```
ls -t doc/plans/plan-*.md | head -1
```

Read the plan. You'll pass its full text to the reviewer.

## Step 2: Identify the diff

**Branch mode** (preferred): if the current branch is not `main`, diff against
main:

```
git diff main...HEAD
git log main..HEAD --oneline
```

**Main mode**: if the user says "review the last N commits" or you're on main,
use the plan's date and commit messages to identify the relevant commits. Ask
the user to confirm the range if ambiguous, then:

```
git diff <base>..<tip>
git log <base>..<tip> --oneline
```

Collect the full diff and the commit log. You'll pass both to the reviewer.

## Step 3: Gather context files

Read these files and include them in the reviewer prompt:

- `CLAUDE.md` — repo conventions, workspace layout, TDD workflow, commit style
- The plan's **Verification** section (test matrix) — extract it specifically
  so the reviewer can check coverage
- `doc/refs/review-calibration.md` — few-shot examples of high-quality review
  comments that calibrate the reviewer's style and specificity

## Step 4: Launch the reviewer

Spawn a **new agent** with `subagent_type: "feature-dev:code-reviewer"` and
`model: "sonnet"`. This agent has no context from the current conversation —
that's the point. It reviews the code independently. Sonnet is sufficient
for review work (reading comprehension + pattern matching) and keeps cost
down.

The prompt you send must be self-contained. Include:

1. The full plan text
2. The full diff
3. The commit log
4. The repo conventions from CLAUDE.md (workspace layout, commit style, test
   conventions, feature-gate conventions)
5. The calibration examples from `doc/refs/review-calibration.md` (read the
   file and include its full contents under `## Examples of high-quality
   review comments`)
6. The review checklist (below)

### Reviewer voice and calibration

The reviewer should write like a thorough human PR reviewer, not a checklist
robot. Good review comments share these qualities:

- **Cite the contract, then the violation.** When the plan says X and the code
  does Y, quote both. "The plan specifies `device = ["dep:tokio", ...]` as an
  optional feature gate (T1), but `Cargo.toml` lists tokio as unconditional."

- **Name the consequence.** Don't just say "this differs from the plan." Say
  what breaks: "This means crate-foo links tokio despite only using sync code,
  adding ~3s to clean builds."

- **Distinguish severity.** Some findings block the merge, others are
  improvement opportunities. Be explicit: "Must fix before merge" vs
  "Consider for a follow-up."

- **Don't pad.** If a section has no findings, one sentence: "All N planned
  tests are present and correctly gated." Don't invent concerns to fill space.

### Reviewer prompt template

~~~
You are reviewing a completed sprint. Your job is to compare the plan against
what was actually implemented and flag gaps, drift, and quality issues.

You are an independent reviewer — you did not write this code and you have
no context beyond what's provided here. Review what you see, not what you
assume.

## Plan

{full plan text}

## Diff (main...branch or commit range)

{diff}

## Commit log

{commit log}

## Repo conventions

{CLAUDE.md excerpt: workspace layout, commit style, test conventions,
feature-gate conventions}

## Examples of high-quality review comments

{contents of doc/refs/review-calibration.md}

Match this style: cite the contract (doc, plan, or naming), show how the
code violates it, and name the consequence. When something is fine, one
sentence is enough. Don't invent concerns to fill space.

## Review checklist

For each section, state what you found concretely. When something is wrong,
cite the specific file, line, plan section, and consequence. When something
is fine, one sentence is enough — don't pad.

### Plan Conformance

Walk every task (T1, T2, ...) and every row in the Verification table:

- Was each task implemented? If partially, what's missing?
- For each planned test, does a corresponding test exist in the diff?
- Were any features, config options, Cargo.toml entries, or feature gates
  described in the plan but absent from the implementation? This is the
  highest-value check — plans often specify build configuration (optional
  deps, feature flags, conditional compilation) that gets lost in
  implementation.
- Were any API signatures or type definitions changed from the plan without
  a documented reason in the commit message or plan's Review section?
- Is there code in the diff that wasn't in the plan? If so, is it a
  justified emergent requirement or undocumented scope creep?

### Code Quality

- Does the code follow repo conventions (thiserror in libs, fixture_or_skip
  for missing test data, no unsafe, lints via Cargo.toml)?
- Are error messages specific enough to diagnose failures from a log line
  alone?
- Is there unintended coupling between crates that should be independent?
- Any redundant code, dead code, or clippy-level issues?

### Test Coverage

**Property tests are the highest-priority check in this section.**

- Walk the plan's **Properties (must pass)** table row by row. For each
  planned property:
  - Does a corresponding `proptest!` block exist in the diff?
  - Does the property assert the invariant described in the plan, or a
    weaker/different one?
  - Is the property `#[ignore]`d? If so, is the reason documented in
    the plan's Review section with a re-enablement plan? An ignored
    property without documentation is a **must-fix**.
- For any module that parses, encodes, or transforms data: are there
  property tests? If the plan didn't list them, flag this as a gap —
  the convention requires proptest for all parse/encode/transform code.
- Compare the plan's **Spot checks** table against actual unit test
  functions. List any that are missing or renamed without explanation.
- Do fixture-gated tests use `fixture_or_skip!` from the core crate
  (return early when fixture is absent, don't panic, don't `#[ignore]`)?
- What edge cases do the tests miss? Be specific — "what happens if the
  connection drops mid-message" is useful; "more tests would be good" is
  not.

### Risks

- TODOs, stubs, or placeholder implementations left in the code?
- Could any change break existing functionality in other crates?
- Security: path traversal in file operations? Command injection?
  Unsanitized input passed to shell commands?
- Dependency concerns: are new deps justified, pinned, and actively
  maintained?

### Recommendations

Separate into two lists:

**Must fix before merge:**
- Issues that violate the plan's stated design, break conventions, or
  introduce bugs.

**Follow-up (future sprint):**
- Improvements, refactoring opportunities, or gaps that are acceptable
  for now but should be tracked.

## Output format

Structure your review as markdown with the five H3 sections above. Be
direct and specific. Cite file paths and line numbers. If the plan
specified something and the code doesn't match, quote both side by side.

Keep the total review under 400 lines. Prioritize findings by impact —
a missing feature gate that affects build times for every consumer is
more important than a suboptimal variable name.
~~~

## Step 5: Place the output and stop

When the reviewer agent returns:

1. **Append the full review to the plan doc** under `## Review` as a new
   subsection:

   ```markdown
   ### Code Review (YYYY-MM-DD)

   {reviewer output}
   ```

   This goes after any existing Review subsections. The coder's retrospective
   and the independent review live side by side — don't overwrite anything.

   If the plan doc doesn't have a `## Review` section, create one.

2. **Print a brief summary to the conversation**: how many must-fix items,
   how many follow-ups, and the path to the plan doc. One paragraph max.

3. **Stop.** Do not attempt to fix any issues the reviewer found. Do not
   offer to fix them. The user will read the review and decide what to do
   next. The review is an artifact, not an action.
