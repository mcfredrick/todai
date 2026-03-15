# Project Instructions

## Architecture

Tenkai is an autonomous daily AI news blog hosted on GitHub Pages from this repo.

- **Pipeline**: `model_selector.py` → `research_agent.py` → `writing_agent.py` → Hugo build → gh-pages deploy
- **Scheduling**: GHA cron `0 8 * * *` (08:00 UTC). Guard step prevents re-running agents if today's post already exists; Hugo build+deploy always runs.
- **LLMs**: OpenRouter free tier only. Model selector picks dynamically at runtime — writing agent rotates through all free models on 429, waits 15s between attempts.
- **Deduplication**: `agents/seen.json` (committed) tracks published URLs with 60-day rolling window.
- **Content**: `content/posts/YYYY-MM-DD.md` — one post per day, committed by the workflow bot.
- **Theme**: `themes/tenkai/` — minimal custom Hugo theme, no JS, no external dependencies.

## Key Operational Notes

- **OpenRouter rate limits**: Free-tier models share upstream rate limits. Running the pipeline multiple times in a day exhausts quotas. The 90s cooldown between research and writing agents helps but doesn't fully protect against it. Don't trigger `workflow_dispatch` more than once per day unless debugging.
- **Hugo baseURL**: Must have a trailing slash (`https://mcfredrick.github.io/todai/`). Without it, `relURL` doesn't prepend the subpath. All theme URLs use `relURL`/`absURL` without a leading slash (e.g. `"style.css" | relURL`, not `"/style.css" | relURL`).
- **GitHub Pages source**: `gh-pages` branch, root `/`. The workflow deploys `public/` there via `peaceiris/actions-gh-pages@v4`.
- **Secrets**: `OPENROUTER_API_KEY` in repo Settings → Secrets. No other secrets needed.
- **Repo push conflicts**: The workflow commits to `main` (the post + seen.json). Always `git pull --rebase` before pushing local changes to avoid non-fast-forward rejections.

## Workflow Standards

### PR Size & Reviewability

- 300-500 lines maximum per PR; split larger features into sequential PRs
- Each PR should be a coherent, reviewable unit
- Never mix refactors with features in the same PR
- PR descriptions are mandatory — explain intent, highlight key areas, note non-obvious decisions

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
