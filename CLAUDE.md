# Project Instructions

## Architecture

Tenkai is an autonomous daily AI news blog hosted on GitHub Pages from this repo.

- **Pipeline**: `model_selector.py` → `research_agent.py` → `writing_agent.py` → `validate_post.py` → Hugo build → gh-pages deploy
- **Scheduling**: GHA cron `0 8 * * *` (08:00 UTC). Guard step prevents re-running agents if today's post already exists; Hugo build+deploy always runs.
- **LLMs**: OpenRouter free tier only. Model selector picks dynamically at runtime — writing agent retries the preferred model up to 3× with 30/60/120s backoff before rotating through all free models. Responses missing `##` sections with linked items are rejected and the next model is tried.
- **Validation**: `agents/validate_post.py` runs after writing and gates the commit. If validation fails the workflow retries writing up to 3 times before failing loudly and creating a GitHub issue.
- **Research caching**: `research.json` is uploaded as a GHA artifact (7-day retention) after every research run. Use `workflow_dispatch` with `skip_research: true` to reuse it without re-running the full research pipeline (e.g. when fixing a bad post without burning rate limits).
- **Deduplication**: `agents/seen.json` (committed) tracks published URLs with 60-day rolling window.
- **Content**: `content/posts/YYYY-MM-DD.md` — one post per day, committed by the workflow bot.
- **Theme**: `themes/tenkai/` — minimal custom Hugo theme, no JS, no external dependencies.

## Key Operational Notes

- **OpenRouter rate limits**: Free-tier models have per-minute upstream limits, not daily quotas. The 90s cooldown between research and writing agents reduces the chance of the writing agent hitting a cooldown left by research. If the preferred writing model is still rate-limited, the 3× backoff loop (30/60/120s) usually clears it before falling back to other models.
- **Recovering a broken post**: If today's post is malformed or missing, delete it via the GitHub API, then trigger `workflow_dispatch` with `skip_research: true` to reuse the cached `research.json` artifact — no need to re-run research. If the artifact is gone (older than 7 days or first run of the day), omit `skip_research` to run the full pipeline.
- **Hugo baseURL**: Must have a trailing slash (`https://mcfredrick.github.io/tenkai/`). Without it, `relURL` doesn't prepend the subpath. All theme URLs use `relURL`/`absURL` without a leading slash (e.g. `"style.css" | relURL`, not `"/style.css" | relURL`).
- **GitHub Pages source**: `gh-pages` branch, root `/`. The workflow deploys `public/` there via `peaceiris/actions-gh-pages@v4`.
- **Secrets**: `OPENROUTER_API_KEY` in repo Settings → Secrets. No other secrets needed.
- **Repo push conflicts**: The workflow commits to `main` (the post + seen.json). Always `git pull --rebase` before pushing local changes to avoid non-fast-forward rejections.

## Workflow Standards

### PR Size & Reviewability

- 300-500 lines maximum per PR; split larger features into sequential PRs
- Each PR should be a coherent, reviewable unit
- Never mix refactors with features in the same PR
- PR descriptions are mandatory — explain intent, highlight key areas, note non-obvious decisions

## UI & Theme Standards

- **All UI elements must use CSS variables** — never hardcode colors, backgrounds, or borders. Use `var(--text)`, `var(--accent)`, `var(--surface)`, `var(--border)`, `var(--muted)`, `var(--dim)`, `var(--glow)` etc.
- **Test both themes** — any new UI feature must be verified in both dark and light mode before shipping.
- **No inline styles with static values** — Hugo syntax highlighting must use `noClasses = false` (class-based) so the theme controls colors, not the highlighter.
- **Interactive states** — hover, active, and focus states should use `var(--accent)` and `var(--glow)` to match the existing pattern.

## Code Quality Standards

### Comments

- Comments explain **why**, never **what** — code should be self-explanatory
- Delete comments that restate what the code does

### Simplicity

- **Single code path**: One clean implementation, no legacy fallbacks
- **No over-engineering**: Don't add abstraction layers until you need them twice
- **No defensive overkill**: Don't handle errors that can't realistically occur
- **Trust established libraries**: Use them directly, don't wrap with defensive code
- **Delete dead code**: Remove it completely, don't comment it out

### Testing

- Tests verify **your** logic, not that libraries work
- Don't test framework features (validation, routing, serialization) or standard library behavior
- Fewer meaningful tests > many trivial tests
- If a test only exercises mocks, delete it
- Assert on observable output, not mock internals; exception: verifying a meaningful cost property (e.g., skipping expensive calls)
- Use parameterization to combine tests that share the same assertion with different inputs
- Each test should verify a distinct behavioral property; if removing it leaves no behavior uncovered, it was redundant
- **Litmus test**: if the test would still pass with a completely wrong implementation of *your* code, it's testing the framework, not your logic

### Data & Validation

- Validate at system boundaries (user input, external APIs), trust internal code
- Fail fast on invalid data — prefer clear errors over silent fallbacks
- Use required fields for essential configuration, not defaults that hide problems

### Naming

- Clear but not verbose: `user_count` not `total_number_of_users_in_system`
- Use precise names — `task_list` not `futures` when items aren't actually futures
- Consolidate duplicated logic — three copies means it needs a function

### Error Handling

- Use `debug` for operational details; reserve `info` for meaningful state transitions
- Let exceptions bubble up — don't catch, log, and re-raise at every level
- Only catch exceptions you can meaningfully handle
