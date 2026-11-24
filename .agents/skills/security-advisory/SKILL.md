---
name: security-advisory
description: Work through a GitHub security advisory from intake to a reviewed fix, pausing for user approval before implementing and before opening the PR. Use when the user wants to analyze a security advisory and prepare a fix branch, PR, and review request.
---

# Security Advisory → Fix PR

Drive a GitHub security advisory from intake to a pull request in the advisory's private
fork, with review assignment.

**Read the `SKILL.md` in the sibling `issue-to-pr` directory and follow it** (relative to
this file: `../issue-to-pr/SKILL.md`; in the repo: `.agents/skills/issue-to-pr/SKILL.md`),
with "issue" read as "advisory", and with the differences below. Where this file and
`issue-to-pr` disagree, this file wins.

**Non-disclosure overrides everything in `issue-to-pr`:** nothing about the advisory may
reach the public repository or any public place — no pushed branch or commit on the public
repo, no public issue, PR, comment, or sprint board item. Anything written down (e.g. the
assessment when the user stops at Gate 1) stays private: the working file or the advisory
itself.

## Setup

- The `project` scope is not needed: there is no public issue, so skip `issue-to-pr`'s
  assignment and sprint board steps (after Gate 1 and in Phase 4).
- Instead of checking out the latest `release/5.x` branch, confirm the current branch is
  the default branch (`gh repo view --json defaultBranchRef`). If not, tell the user which
  branch is checked out and ask whether to switch — do not switch unasked. The fix branch
  is created in Phase 3 from the release branch picked there.
- Name the working file `security-advisory-<advisory-id>.md`.

## Phase 1 — Understand and assess

Fetch the advisory with `gh api /repos/<owner>/<repo>/security-advisories/<advisory-id>`
instead of `gh issue view`, and read the `description` field in full, not just the
summary/title. The one-line summary
routinely omits scope-defining details (e.g. "mirror the behavior of an older branch" or
"in any of the places X happens"). Read any linked references too.

Grep the whole codebase for other call sites touching the same sensitive data or config flag
the advisory names, not just the one code path that's easiest to spot — the obvious path is
often only one of several, and an under-scoped fix is worse than a slow one.

In addition to what `issue-to-pr` asks you to present, cover:
- the likely impact and the affected components
- as alternatives, whether the issue is better handled by an upstream dependency change, a
  configuration change, or a documentation update

Do not resolve ambiguity about the advisory's scope yourself: raise it as a question at
Gate 1. An under-scoped fix is the outcome to avoid.

## Phase 2 — Plan

Every decision here is security-relevant, so replace `issue-to-pr`'s "a security-relevant
decision" stop condition with: **stop and ask** if the fix approach turns out materially
different from the one approved at Gate 1, or weaker (e.g. mitigating instead of fixing).
The other stop conditions still apply.

## Phase 3 — Execute

GitHub creates a private temporary fork when the advisory is opened. Check for it before
creating a new one:
`gh api /repos/<owner>/<repo>/security-advisories/<advisory-id> --jq .private_fork.full_name`.
If the current repo's `origin` already matches that fork, use it directly. Only create a
new fork if one doesn't already exist.

Determine the fix target branch: **default to the latest release branch**, not the
repo's default branch — that's what's actually shipped, and what a security fix needs to
land on. List branches matching `release/<major>.<minor>` on the upstream repo (e.g.
`gh api repos/<owner>/<repo>/branches --paginate --jq '.[].name' | grep -E
'^release/[0-9]+\.[0-9]+$'`) and pick the highest by semantic version. Branch from that
release branch (not from the fork's default branch). If no `release/*` branches exist, fall
back to the default branch. State which branch was picked and why at Gate 2 — this is a
default, not a silent choice, and the user can redirect it.

Before presenting anything, run `git status` and `git diff --stat` and check that every
changed file is actually part of the fix. Environment setup in the working copy (creating a
venv, installing dependencies) can leave unrelated lockfile churn (`uv.lock`,
`package-lock.json`, etc.) — revert anything that doesn't belong to the fix before showing
the diff.

In the PR body, leave out the `Closes #` / `Part of #` line: there is no public issue to link.

## Gate 2

Leave out `issue-to-pr`'s "fully solved / sprints board" item: there is no public issue to
link and no board to update. Also present the fork and branch that will be used, and ask a
second question together with
the decision: whom to request review from — `frankcorneliusmartin`, `bartvanb`, both, or
nobody. GitHub does not allow requesting review from the PR author, so check the current
user with `gh api user --jq .login` and leave that account out of the options.

## Phase 4 — Submit and request review

This replaces Phase 4 of `issue-to-pr`, including its "After the PR is opened" steps.

- Commit the change and push the branch to the temporary fork only. Check `git remote -v`
  first and push to the fork's remote explicitly (`git push <fork-remote> <fix-branch>`).
  **Never push to the public upstream repository**: a pushed branch discloses the fix as
  surely as a PR does.
- **Open the pull request within the temporary private fork itself — base and head both
  in the fork repo** (e.g. `gh pr create --repo <owner>/<fork-repo> --base
  <release-branch> --head <fix-branch> ...`, plus `--draft` if chosen). **Never open it
  against the public upstream repository.** The fork is private specifically so the
  unpatched vulnerability isn't disclosed before the advisory is published; opening the PR
  against the public upstream repo publishes those details immediately, and a closed PR
  there is not enough to undo the exposure. Since both branches live in the same (fork)
  repo, this is a plain same-repo PR — no cross-repo head resolution involved.
- If requested, request review from the chosen reviewer(s) on the fork's PR — use
  `gh api repos/<owner>/<fork-repo>/pulls/<number>/requested_reviewers -X POST -f
  'reviewers[]=<reviewer>'` (one `-f` per reviewer) directly rather than
  `gh pr edit --add-reviewer`, which can fail on an unrelated GraphQL error about deprecated
  Projects-classic fields (`repository.pullRequest.projectCards`) even though the request has
  nothing to do with project boards. Verify with
  `gh api repos/<owner>/<fork-repo>/pulls/<number>/requested_reviewers`. The PR number only
  exists in the fork; the same number upstream is an unrelated public PR.

Return the PR URL and the review request status.

## Backports to other release lines

When the user asks for the same fix on another release branch (e.g. `release/4.16`
after the fix landed on `release/5.0`), work in the **existing advisory checkout**: do not
create a separate clone or `git worktree` for it. Commit or otherwise finish the current
branch, then create a new branch there from the target release branch (e.g.
`git switch -c <fix-branch>-<version> origin/<release-branch>`), so the user finds all the
work for the advisory in one folder. Release lines may need a different dev environment
(Python version, pinned `requirements.txt`, install command); set it up the way that
branch's CI workflow (`.github/workflows/`) does before running tests. Phase 3's diff
check, Gate 2, and Phase 4 (push and PR within the private fork only) all apply to each
backport.

Only backport to the latest release line of each *older major* version (e.g.
`release/4.16` when the fix landed on `release/5.1`). Do not backport to older minor lines
of the same major (e.g. `release/5.0` when the fix is on `release/5.1`): the latest minor
is enough.
