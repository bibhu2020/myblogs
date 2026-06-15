Perform a full git check-in to the `local` branch and open a PR into `main`. Follow these steps exactly:

**Branch rule:** Never commit directly to `main`. All work goes to `local` first, then into `main` via PR only.

**Optional hint from user:** $ARGUMENTS (use this as the commit message theme/context if provided; otherwise infer from the diff)

---

### Step 1 — Ensure we are on `local`

Run `git branch --show-current`. If the result is `main`, **immediately warn the user**: "⚠️ You are currently on `main`. Your working branch is `local`. Moving your changes there now." Then stash all changes (`git stash push --include-untracked`), switch to `local`, and apply the stash (`git stash pop`) before continuing.

If already on `local`, proceed.

### Step 2 — Inspect changes

Run `git status` and `git diff HEAD` to understand what changed. Identify all modified, added, and deleted files.

### Step 3 — Stage and commit

- Stage only relevant files (avoid `.env`, secrets, large binaries unless clearly intentional).
- Draft a commit message that follows the existing style in `git log --oneline -10`:
  - Use conventional commits: `feat:`, `fix:`, `refactor:`, `chore:`, etc.
  - First line ≤ 72 chars, imperative mood.
  - If the diff is substantial, add a short body paragraph.
- Commit using a HEREDOC to preserve formatting. End the commit message with:
  `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`

### Step 4 — Push to origin/local

Run `git push origin local`. If the branch has no upstream yet, use `git push -u origin local`.

### Step 5 — Create a PR from `local` → `main`

Use `gh pr create` with:
- A concise title (≤ 70 chars)
- A body that includes:
  - `## Summary` — bullet points of what changed and why
  - `## Test plan` — checklist of how to verify the change
  - `🤖 Generated with [Claude Code](https://claude.com/claude-code)`
- Base branch: `main`
- Head branch: `local`

If a PR from `local` → `main` already exists (check with `gh pr list --head local --base main`), push the new commit to the existing PR instead of creating a duplicate. Report the PR URL at the end.
