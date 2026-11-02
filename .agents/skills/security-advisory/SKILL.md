---
name: security-advisory
description: Work through a GitHub security advisory from intake to a reviewed fix, pausing for explicit user approval at each phase. Use when the user wants to analyze a security advisory and prepare a fix branch, PR, and review request.
---

# Security Advisory → Fix PR

Drive a GitHub security advisory from advisory intake to a pull request with review assignment in five gated phases.

## The core rule

**Never begin a phase before the user has approved the previous one.** Each gate is a
hard stop: present the deliverable, ask, and wait for a real answer in a new user turn.
Silence, ambiguity, or a partial response is not approval. If the user asks for changes,
revise and re-present the same gate — do not advance.

At each gate, end your turn with an explicit question listing the options, and do not
continue until the user answers. If your tool has a structured question tool (e.g.
`AskUserQuestion` in Claude Code), use it.

## Setup

Verify `gh auth status` succeeds. If not, stop and tell the user to run `gh auth login` —
nothing in this workflow works without it.

Check the repo state before anything else:
- Determine the default branch (`gh repo view --json defaultBranchRef`) and confirm the
  current branch matches it. If not, tell the user which branch is currently checked out
  and ask whether to switch to the default branch first — do not switch unasked.
- Run `git status`. If there are uncommitted changes (staged, unstaged, or untracked),
  stop and tell the user what's dirty. Ask how to proceed (stash, commit, or abandon the
  workflow) rather than working on top of it.

Only proceed to Phase 1 once the branch and working tree are confirmed clean.

Create a working file `security-advisory-<advisory-id>.md` outside the repository (your
tool's scratchpad directory if it has one, otherwise a temp directory) and record each
approved artifact in it as you go.

---

## Phase 1 — Read and restate

Fetch the advisory from GitHub using the advisory URL or identifier. Use the GitHub CLI to
read the advisory details and any linked references. If authentication is required, use the
user's existing `gh` authentication context.

Read the advisory carefully and also inspect the referenced code paths or repository context
that the advisory mentions.

Fetch the advisory's full description via the API, not just the summary/title — use
`gh api /repos/<owner>/<repo>/security-advisories/<advisory-id>` and read the `description`
field in full. The one-line summary routinely omits scope-defining details (e.g. "mirror the
behavior of an older branch" or "in any of the places X happens").

Grep the whole codebase for other call sites touching the same sensitive data or config flag
the advisory names, not just the one code path that's easiest to spot — the obvious path is
often only one of several, and an under-scoped fix is worse than a slow one.

Present:
- What the advisory says, in your own words
- The likely impact and affected components
- Any ambiguity or missing context that needs clarification
- Relevant existing code, as `file:line` links

**Gate 1:** Is this an accurate reading of the advisory?

## Phase 2 — Assess

Give a real opinion about whether the advisory should be addressed and how.

Cover:
- Whether the proposed fix is a good idea, and why
- Whether it fits the codebase's architecture and conventions
- Cost, blast radius, and what it risks breaking
- Alternatives, including whether the issue is better handled by upstream dependency
  changes, configuration changes, or a documentation update

Do not soften a negative verdict into a neutral one. If the honest read is that the advisory
is not actionable or the right fix is outside this repository, say so plainly and explain what
would be done instead.

**Gate 2:** Proceed / proceed with a modified goal / stop here.

## Phase 3 — Plan

If your tool has a plan mode (e.g. `EnterPlanMode`/`ExitPlanMode` in Claude Code), use it;
otherwise present the plan as a message. Make no file edits during this phase. Write a
step-by-step implementation plan, including:
- files to touch
- the change in each file
- the expected behavior after the fix
- tests to add or update
- anything deliberately left out of scope
- any assumptions or open questions resolved by judgement

**Gate 3:** Request approval of the plan. Do not advance until the user explicitly approves it.

## Phase 4 — Execute

For a GitHub security advisory, GitHub already creates a private temporary fork when the
advisory is opened. Check for it before creating a new one:
`gh api /repos/<owner>/<repo>/security-advisories/<advisory-id> --jq .private_fork.full_name`.
If the current repo's `origin` already matches that fork, use it directly. Only create a
new fork if one doesn't already exist.

Determine the fix target branch: **default to the latest release branch**, not the
repo's default branch — that's what's actually shipped, and what a security fix needs to
land on. List branches matching `release/<major>.<minor>` on the upstream repo (e.g.
`gh api repos/<owner>/<repo>/branches --paginate --jq '.[].name' | grep -E
'^release/[0-9]+\.[0-9]+$'`) and pick the highest by semantic version. Branch from that
release branch (not from the fork's default branch) and implement the approved plan
there. If no `release/*` branches exist, fall back to the default branch. State which
branch was picked and why when presenting the diff at Gate 4 — this is a default, not a
silent choice, and the user can redirect it.

When a change in approach is necessary, log it in the working file as you go.

Before presenting anything, run `git status` and `git diff --stat` and check that every
changed file is actually part of the fix. Environment setup in the working copy (creating a
venv, installing dependencies) can leave unrelated lockfile churn (`uv.lock`,
`package-lock.json`, etc.) — revert anything that doesn't belong to the fix before showing
the diff.

Present:
- the full diff against the base branch
- the proposed fix summary
- test and validation results as they actually came out
- the running deviation list

**Gate 4:** Ask the user to pick one of three options: approve as-is / request changes /
make manual edits myself.
- **Request changes** — revise the implementation yourself, then re-present the diff and
  validation results from the top of this gate.
- **Manual edits** — tell the user to edit the branch directly and say when they're done.
  When they do, re-run the diff and re-ask this gate.
- Only an outright approval of the diff as it currently stands advances to Phase 5.

## Phase 5 — Submit and request review

Draft a commit message and PR body from what was implemented, structured as:

```markdown
## Summary
<2-4 sentences describing the issue, the change, and any notable reviewer context>

## What this does
<the change, described from the code that exists>

## Approach
<why it was built this way>

## Testing
<what was run and what the results were>
```

Show the user the commit message, the PR title/body, the target branch (the latest
release branch picked in Phase 4, unless the user redirected it), and the fork/branch
that will be used before anything is pushed.

Ask whether the PR should be opened as a draft or ready for review, and whom to request
review from: `frankcorneliusmartin`, `bartvanb`, both, or nobody. GitHub does not allow
requesting review from the PR author, so check the current user with
`gh api user --jq .login` and leave that account out of the options.

**Gate 5:** Approve pushing, committing, and opening the PR, and the review request.

Only after an explicit yes:
- commit the change locally
- push the branch to the temporary fork
- **open the pull request within the temporary private fork itself — base and head both
  in the fork repo** (e.g. `gh pr create --repo <owner>/<fork-repo> --base
  <release-branch> --head <fix-branch> ...`). **Never open it against the public
  upstream repository.** The fork is private specifically so the unpatched vulnerability
  isn't disclosed before the advisory is published; opening the PR against the public
  upstream repo publishes those details immediately, and a closed PR there is not enough
  to undo the exposure. Since both branches live in the same (fork) repo, this is a
  plain same-repo PR — no cross-repo head resolution involved.
- if requested, request review from the chosen reviewer(s) — use
  `gh api repos/<owner>/<repo>/pulls/<number>/requested_reviewers -X POST -f
  'reviewers[]=<reviewer>'` (one `-f` per reviewer) directly rather than
  `gh pr edit --add-reviewer`, which can fail on an unrelated GraphQL error about deprecated Projects-classic fields
  (`repository.pullRequest.projectCards`) even though the request has nothing to do with
  project boards. Verify with `gh api repos/<owner>/<repo>/pulls/<number>/requested_reviewers`.

Return the PR URL and the review request status.

## Backports to other release lines

When the user asks for the same fix on another release branch (e.g. `release/4.16`
after the fix landed on `release/5.0`), work in the **existing advisory checkout**: do not
create a separate clone or `git worktree` for it. Commit or otherwise finish the current
branch, then create a new branch there from the target release branch (e.g.
`git switch -c <fix-branch>-<version> origin/<release-branch>`), so the user finds all the
work for the advisory in one folder. Release lines may need a different dev environment
(Python version, pinned `requirements.txt`, install command); set it up the way that
branch's CI workflow (`.github/workflows/`) does before running tests. Gate 4 and Gate 5
still apply to the backport.

---

## Conventions

- Do not attribute commits or PRs to the AI assistant: no `Co-Authored-By` trailer, no
  "Generated with" line, no mention of the assistant or tool in commit messages or PR
  bodies.
- Honour any `CONTRIBUTING.md`, `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`,
  or PR template in the repo; they override the defaults here.
