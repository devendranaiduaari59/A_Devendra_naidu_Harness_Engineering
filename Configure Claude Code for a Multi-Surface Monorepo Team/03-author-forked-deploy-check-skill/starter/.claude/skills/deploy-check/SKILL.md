---
name: deploy-check
description: Run read-only pre-deployment validation in a forked sub-agent and report a single pass/fail summary back to the main session
context: fork
argument-hint: "[target-branch] (defaults to main)"
allowed-tools:
  - Read
  - Grep
  - Glob
  - "Bash(git status:*)"
  - "Bash(git diff:*)"
  - "Bash(git log:*)"
  - "Bash(git rev-parse:*)"
  - "Bash(git ls-files:*)"
  - "Bash(gh pr view:*)"
  - "Bash(gh pr checks:*)"
---

# /deploy-check

Runs the team's pre-deployment validation checklist against the current working tree and the branch you're about to ship. Read-only by design — this skill never modifies files, never pushes, never deploys. It returns a single structured summary so the calling session can decide whether to proceed.

## Why this is a skill (not a CLAUDE.md addition)

This is a skill because the deploy validation is **on-demand, forked, and task-specific**. It is only needed immediately before deployment and can produce verbose intermediate output while inspecting files, diffs, and checks.

CLAUDE.md is for **always-loaded, universal conventions** that every session needs, such as project-wide coding conventions or error-handling rules. Keeping deploy-specific investigation in a skill avoids putting unnecessary detail into every session's context.

Rule of thumb: **on-demand / forked / task-specific → skill; always-loaded / universal → CLAUDE.md.**

## Why `context: fork`

The fork keeps verbose intermediate output **out of the main session / conversation**. A deploy check may walk the working tree, inspect diffs, and perform several enumeration passes; those details have no value in the calling session once the final ship/no-ship status is known. Only the structured summary should return to the main conversation.

`context: fork` is a **Claude Code product feature operating at the skill-invocation layer**. It is conceptually analogous to the Architect's Playbook **Branching Reality** pattern, which describes session-level forking through `fork_session`. Both approaches isolate task-specific work while returning the useful result to the calling context.

## Checks

Run all three checks. Each check produces a pass-or-fail verdict; if any fails, the overall summary is **fail**.

### 1. Uncommitted changes

* **Detect:** Run `git status --porcelain`.
* **Pass:** The command returns no output, meaning the working tree is clean.
* **Fail:** The command returns one or more entries. Report that uncommitted changes exist and identify the affected paths in the detail.

### 2. Migrations up-to-date with code

* **Detect:** Inspect the diff from the target branch using `git diff` and use `git ls-files` to verify that migration files exist for migration-required repository or model changes.
* **Pass:** Every migration-required code change has a corresponding migration file in the branch.
* **Fail:** A migration-required change has no corresponding migration file. Report the affected path or change in the detail.

### 3. CI checks green on the open PR

* **Detect:** Run `gh pr view --json statusCheckRollup` and inspect the pull request check statuses.
* **Pass:** All required CI checks report `SUCCESS`.
* **Fail:** Any required check is failing, pending, cancelled, or otherwise not successful. Report the check name and status in the detail.

## Output format

Return exactly this shape to the main session:

```text
verdict: pass | fail

checks:
  - name: <check-name>
    status: pass | fail
    detail: <one line or empty>
```

Do not include raw `git status`, raw diff hunks, or full check logs in the returned summary. Those details stay in the fork. If the author wants to investigate a failed check, they can re-invoke the skill targeting that single check or run the underlying command themselves.

## Personalization

This skill is project-scoped because it lives at `.claude/skills/deploy-check/`, so the same deploy validation rules are available to the whole team through the repository.

A teammate who wants a stricter personal variant can create a parallel skill such as `~/.claude/skills/deploy-check-strict/` with a different name. For example, their personal variant could additionally fail when a diff exceeds 500 lines without a sufficiently detailed PR description. Because that variant lives in the user's home configuration rather than the repository, it is not committed and does not affect teammates.

## What this skill deliberately does not do

* It never pushes, deploys, or runs migrations. The `allowed-tools` allowlist is read-only by construction.
* It does not run the test suite. Tests have their own pre-merge gate in CI; duplicating that here would slow every deploy check without adding signal.
* It does not check for secrets in code. That is the job of the `gitleaks` pre-commit hook, which fails the commit rather than the deploy check.
