# Context Management Strategy

Context is the scarce resource in this whole pipeline — both literally (an
LLM's context window) and economically (tokens cost money and latency on
every PR push). Every design choice below exists to keep some agent from
reading more than it needs.

## 1. Summarize before fanning out
[`pr-explorer`](../../.claude/agents/pr-explorer.md) reads the diff once and
produces a capped (~200 line) summary. The three review subagents read
*that summary*, not the raw diff plus the full repo. This means "understand
what changed" happens once instead of three times, and the expensive part
(deciding whether a hunk needs full-file context) is a decision the
explorer makes per-file, not something every reviewer redoes.

## 2. Hunks, not files
Both the explorer and reviewers default to diff hunks. A full file is only
opened when a hunk is ambiguous without surrounding code, and even then
only that one file — never "read the whole repo to be safe." This is
written explicitly into each agent's instructions (see the "What NOT to do"
sections) because it's the single biggest lever on token usage: a 15-line
hunk costs a few hundred tokens, the file it lives in can cost thousands.

## 3. Tool scoping per subagent
Each subagent's frontmatter lists only the tools it needs:
- `pr-explorer`: `Bash, Read, Grep, Glob` (needs `git diff`).
- The three reviewers: `Read, Grep, Glob` only — no `Bash`, so they can't
  independently decide to `cat` half the repo or re-run `git diff`
  themselves; they work from what the explorer already handed them.

Narrower tool access isn't just a safety property here — it's a context
property. An agent that *can't* run arbitrary shell commands can't
accidentally pull a huge command output into its own transcript.

## 4. Mechanical aggregation, not another LLM pass
Merging the three reviewers' findings into one comment (dedupe, drop
uncategorized findings, compute the Merge / Merge-with-changes / Do-not-merge
line) is done with plain code, not a fourth LLM call. An aggregator agent
would need to re-read all three outputs in full anyway with no judgment call
beyond "combine these" — a job code does deterministically for free.

## 5. One consolidated pass in production, subagents for depth
The four-subagent pipeline above is how the review logic was *built and
validated* (see [09-parallel-sessions.md](05-parallel-sessions.md)) and how
a human operator can request a deeper look. The default, always-on CI path
([`openai_pr_review.py`](../../.github/scripts/openai_pr_review.py)) makes a
**single** OpenAI call per PR event with one prompt that encodes the same
four category definitions. Running four separate live LLM subagent sessions
on *every* push to *every* PR would multiply cost and latency 4x for
marginal gain on typical small PRs — the categories transfer without
needing four round-trips every time. The subagent architecture stays
available (via Claude Code, interactively or in a scheduled/background run)
for large or high-risk PRs where the deeper, parallelized pass is worth the
cost.

## 6. Bounding the diff sent to the LLM
`openai_pr_review.py` truncates the diff to `MAX_DIFF_CHARS` (60,000 chars)
before sending it, and says so explicitly in the prompt when it does. An
oversized diff degrading review quality is preferable to a request that
fails outright or silently drops context without saying so.

## 7. One comment, edited in place
The workflow searches for its own previous comment (via an HTML marker) and
updates it instead of posting a new one on every push. This isn't just
tidiness — an unbounded, growing comment thread is exactly the kind of
context bloat that makes a *human* re-reviewing the PR (or a future bot run
that reads PR comments for context) have to wade through N stale reviews to
find the current one.

## 8. Static checks run before the LLM call, cheaply
[`static_checks.py`](../../.github/scripts/static_checks.py) does the
deterministic, pattern-matchable subset of the review logic (secrets
patterns, debug prints, TODO markers, naive missing-test detection) with no
LLM call at all. This keeps token spend reserved for the checks that
actually require judgment, and gives instant, free, deterministic feedback
(also why it's the part covered by TDD in
[04-tdd-tests.md](04-tdd-tests.md) — it has no nondeterminism to fight).
