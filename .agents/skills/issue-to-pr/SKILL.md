---
name: issue-to-pr
description: Take a GitHub issue URL through assessment, planning, implementation, and PR creation, pausing for explicit user approval at every phase. Use when the user provides a GitHub issue URL and wants it worked through end to end, or invokes /issue-to-pr.
---

# Issue → PR

Drive a GitHub issue from URL to open pull request in five gated phases.

## The core rule

**Never begin a phase before the user has approved the previous one.** Each gate is a
hard stop: present the deliverable, ask, and wait for a real answer in a new user turn.
Silence, ambiguity, or a partial response is not approval. If the user asks for changes,
revise and re-present the *same* gate — do not advance.

At each gate, end your turn with an explicit question listing the options, and do not
continue until the user answers. If your tool has a structured question tool (e.g.
`AskUserQuestion` in Claude Code), use it. For Gate 3, use the tool's plan mode if it
has one — see Phase 3.

## Setup

Verify `gh auth status` succeeds. If not, stop and tell the user to run `gh auth login` —
nothing in this workflow works without it. Also check that the token scopes include
`project` (needed in Phase 5 to update the sprint board). If missing, tell the user to run
`gh auth refresh -s project`; this is not a blocker for the earlier phases.

Check the repo state before anything else:
- The base branch is always the latest `release/5.x` branch, not the default branch.
  Find it with `git ls-remote --heads origin 'release/5.*'` and pick the highest version
  of the form `release/5.<minor>` (ignore suffixed one-off branches such as
  `release/5.0.0b1-...`). Confirm the current branch matches it. If not, tell the user
  which branch is checked out and ask whether to switch — do not switch unasked. Phase 4
  branches off it and Phase 5 targets it with `gh pr create --base <branch>`.
- Run `git status`. If there are uncommitted changes (staged, unstaged, or untracked),
  stop and tell the user what's dirty. Ask how to proceed (stash, commit, or abandon the
  workflow) rather than working on top of it — Phase 4 branches off this state, and a
  dirty starting point makes for a dirty PR.

Only proceed to Phase 1 once the branch and working tree are confirmed clean, since
Phase 4 will branch off of whatever is checked out now.

Create a working file `issue-to-pr-<issue-number>.md` outside the repository (your tool's
scratchpad directory if it has one, otherwise a temp directory) and record each
approved artifact in it as you go. Phase 5 depends on the approved plan still being
readable verbatim, so do not skip this.

---

## Phase 1 — Read and restate

Fetch the issue with `gh issue view <url> --comments --json title,body,labels,comments,state,number`.
Read the linked code it references. Read the discussion in the comments, not just the body —
issues are frequently amended or redirected there.

Present:
- What the issue actually asks for, in your own words
- What the reporter seems to want underneath that, if it differs
- Any ambiguity you had to resolve, and how you resolved it
- Relevant existing code, as `file:line` links

**Gate 1:** Is this an accurate reading of the issue?

## Phase 2 — Assess

Give a real opinion. This phase exists because not every issue should be built, and the
user asked to hear that before work starts, not after.

Cover:
- Whether the change is a good idea, and why — a clear verdict, not a survey
- Whether it fits the codebase's existing architecture and conventions
- Cost, blast radius, and what it risks breaking
- Alternatives, including "resolve as won't-fix" or "the reporter's real problem is
  better solved another way", when either is genuinely the better call

Do not soften a negative verdict into a neutral one. If the honest read is that the issue
is misconceived, say so plainly and explain what you'd do instead.

**Gate 2:** Proceed / proceed with a modified goal / stop here.
If the user stops, write the assessment somewhere durable if they want it, and end.

## Phase 3 — Plan

If your tool has a plan mode (e.g. `EnterPlanMode`/`ExitPlanMode` in Claude Code), enter
it before drafting anything, so the user can review and comment on specific lines of the
plan rather than only accepting or rejecting the whole thing. Otherwise present the plan
as a message. Either way, make no file edits during this phase.

Write a step-by-step implementation plan: files touched, the change in each, new
behaviour, tests to add or update, and anything deliberately left out of scope. Name the
open questions you're deciding by judgement and what you decided.

**Gate 3:** Request approval of the plan (via plan mode's approval step if available). If
the user comes back with comments or requested changes, revise the plan and request
approval again — do not advance on a partial or conditional approval, same as every other
gate. Repeat until the user approves outright.

Once approved, copy the final plan into the working file **verbatim** — Phase 5 diffs
against it, and a plan-mode file or chat message is not guaranteed to persist past this
phase.

## Phase 4 — Execute

Branch first (never commit directly to the base branch). Then implement the approved plan.

Match the surrounding code's idiom, naming, and comment density. Run the project's
tests, linter, and typechecker; if the repo has a `verify` skill or equivalent, use it.

When reality forces a departure from the plan — and it usually does — **log it in the
working file as you go**, with what changed and why. Reconstructing deviations from
memory at the end produces a vague PR description; this list is the thing that makes
Phase 5 worth doing.

If a deviation is large enough to change the plan's shape, stop and raise it
immediately rather than banking it for the end.

Present: the full diff (`git diff` against the branch point — not just a prose summary,
so the user can read the actual code line by line), test/lint/typecheck results **as
they actually came out** (failures reported as failures, with output; skipped steps
named as skipped), and the running deviation list.

**Gate 4:** Ask the user to pick one of three options: approve as-is / request changes /
make manual edits myself.
- **Request changes** — revise the implementation yourself, then re-present the diff,
  test results, and deviation list from the top of this gate. Same rule as every other
  gate: a partial or conditional approval does not advance.
- **Manual edits** — tell the user to edit the branch directly and say when they're
  done. When they do, re-run `git diff`, show what changed since the last presentation,
  and re-ask this gate. Repeat as many rounds as needed.
- Only an outright approval of the diff as it currently stands advances to Phase 5.

## Phase 5 — Pull request

Draft the PR body from what was implemented, structured as:

```markdown
## Summary
<2-4 sentences a reviewer can read in isolation: what problem existed, what changed,
and any notable call the reviewer should know about before reading further (e.g. a
rejected alternative, a scope cut, a risk accepted). This is the part most likely to
be read on its own — write it that way, don't just restate the title.>

<Closes #<number>  — if the PR fully solves the issue
 Part of #<number> — if it only partially addresses it; then skip linking below>

## What this does
<the change, described from the code that exists — not from the plan>

## Approach
<why it was built this way>

## Deviations from the plan
<each departure, with its reason. "None — implemented as planned." if that is true.>

## Testing
<what was run and what the results were>
```

Show the user the body, the target branch, and the commit(s) before anything is pushed.
As part of this gate, ask whether the PR should be opened as a draft or ready for review,
and state whether you consider the issue fully solved (→ it will be linked) and whether
the issue is on the sprints board (→ its status will be set to "To review").

**Gate 5:** Approve pushing and opening the PR, and draft vs. ready-for-review.

Only after an explicit yes: commit, push the branch, and run `gh pr create --base <release branch>` (add `--draft`
if the user chose draft). Return the PR URL. Pushing and opening a PR is outward-facing
and hard to walk back — this gate is never assumed, never inferred from earlier
approvals, and never skipped because the user approved Phase 4.

### After the PR is opened

Both steps below are covered by the Gate 5 approval; report the outcome of each.

**Link the issue (only if the PR fully solves it).** Closing keywords only link and
auto-close when the PR targets the default branch, and these PRs target a release branch.
Check whether the link took:

```bash
gh api graphql -f query='{repository(owner:"<owner>",name:"<repo>"){pullRequest(number:<pr>){closingIssuesReferences(first:5){nodes{number}}}}}'
```

If the issue is not listed, link it in the **Development** sidebar with the
`addCloseIssueReferences` mutation (works for any base branch, idempotent). Do not post a
comment on the issue instead — the user wants the actual Development link.

```bash
gh api graphql -f query='{repository(owner:"<owner>",name:"<repo>"){issue(number:<issue>){id} pullRequest(number:<pr>){id}}}'
gh api graphql -f query='mutation($i:ID!,$p:ID!){addCloseIssueReferences(input:{issueId:$i,pullRequestIds:[$p]}){clientMutationId}}' \
  -f i=<issue node id> -f p=<pr node id>
```

Re-run the `closingIssuesReferences` query to confirm the issue is now listed. If the
mutation fails, report the error and ask the user to link it manually under
**Development** — do not fall back to commenting.

**Set sprint status to "To review" (if the issue is in the sprints project).** Requires
the `project` scope; if missing, tell the user to run `gh auth refresh -s project` and
offer to do this step afterwards. Find the issue's project items:

```bash
gh api graphql -f query='{repository(owner:"<owner>",name:"<repo>"){issue(number:<issue>){projectItems(first:10){nodes{id project{id title} fieldValueByName(name:"Status"){... on ProjectV2ItemFieldSingleSelectValue{name}}}}}}}'
```

Pick the item whose project title contains "sprint" (case-insensitive). If there is none,
skip and say so. Otherwise look up the Status field and its options:

```bash
gh api graphql -f query='{node(id:"<project id>"){... on ProjectV2{field(name:"Status"){... on ProjectV2SingleSelectField{id options{id name}}}}}}'
```

Pick the option matching "to review" (case-insensitive) — if no option matches, stop and
show the user the available options rather than guessing — then set it:

```bash
gh project item-edit --id <item id> --project-id <project id> \
  --field-id <status field id> --single-select-option-id <option id>
```

---

## Conventions

- Do not attribute commits or PRs to the AI assistant: no `Co-Authored-By` trailer, no
  "Generated with" line, no mention of the assistant or tool in commit messages or PR
  bodies.
- Honour any `CONTRIBUTING.md`, `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`,
  or PR template in the repo; they override the defaults here.
