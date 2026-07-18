---
name: commit-and-push
description: Use when the user asks to "commit and push", "commit these changes", "push to github", or wants a Conventional Commits-formatted commit message for this repo. Stages the relevant changed files, drafts a Conventional Commits message (type(scope): description) from the diff, creates the commit, and pushes to the `origin` remote on the current branch.
---

# Commit and Push (Conventional Commits)

Drafts a [Conventional Commits](https://www.conventionalcommits.org/) message from
the current changes, commits them, and pushes to GitHub on the current branch.

## Git identity

This repo's `origin` remote is a GitHub repo owned by account `barunbasis37`
(email `barunbasis37@gmail.com`). Global git config already has `user.email` set
to this address, which is what GitHub uses to attribute commits to the account —
**never modify git config** as part of this skill (per Git Safety Protocol).

## Step 1 — Inspect the changes

Run in parallel:
- `git status` (never `-uall`) to see untracked/modified files
- `git diff` (unstaged) and `git diff --staged` (already staged) to see the actual
  content changes
- `git log -5 --oneline` to match this repo's existing message style/scope naming,
  if prior commits establish a pattern

## Step 2 — Stage files

Add the specific files relevant to the change by name (never `git add -A` or
`git add .`). Before staging, check the contents of any file that could hold
secrets (`.env`, credentials, keys, tokens) even if the filename looks innocuous —
exclude it and warn the user instead of committing it.

## Step 3 — Draft a Conventional Commits message

Format:

```
<type>(<optional scope>): <short imperative summary, ≤72 chars, no trailing period>

<optional body — the *why*, wrapped ~72 cols, only when non-obvious>
```

Pick `<type>` from: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
`build`, `ci`, `chore`, `revert`. Add `<scope>` when the change is localized to
one clear area (a folder, a workflow file, a feature); omit it for repo-wide
changes. Use `!` after the type/scope (e.g. `feat!:`) plus a `BREAKING CHANGE:`
footer only for genuine breaking changes.

## Step 4 — Commit

Create the commit via a HEREDOC, with the trailer:

```
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
```

Run `git status` after to confirm success. If a pre-commit hook fails: fix the
issue, re-stage, and create a **new** commit — never `--amend` a commit that
didn't happen, never `--no-verify`.

## Step 5 — Push

- If the current branch already tracks a remote: `git push`
- If it doesn't yet: `git push -u origin <current-branch-name>`

The push step is pre-authorized by the user for this repository as part of
invoking this skill — don't stop to ask for confirmation before pushing here.
Still follow every other Git Safety Protocol rule: no `--force`, no `--no-verify`,
no rewriting history, new commits instead of amends, never push to a
protected/main branch with `--force`.

## Step 6 — Report

Report the short commit hash, the message's subject line, and confirm the push
succeeded (branch and remote).
