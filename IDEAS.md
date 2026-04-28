# ScraperKit — Ideas & Future Plans

A running backlog of improvements. Pick one and build it.

---

## Quick wins

| Idea | What it does |
|---|---|
| **Re-run button** | One-click repeat of any past run (same config + task) from Run History — no navigating back to Configs |
| **Browser finish notification** | Web Notifications API desktop alert when a crawl completes, so you don't have to watch the console |
| **Live item counter** | Show items scraped so far in the Live Jobs table during the run, updating in real time |

---

## Bigger features

### Scheduled runs
Cron-style scheduling from the dashboard — set "project → full every Monday at 07:00" and forget it.
The job fires automatically, logs to Run History like any other run.

### Parallel "Run all"
A single button that fires all project configs simultaneously instead of one at a time.
For three projects (project + project + project) this cuts total crawl wall-clock time by ~3x.

### Bulk history operations
Select multiple runs with checkboxes → delete all at once.
Useful after testing when you accumulate dozens of short test runs.

---

## Crawl performance

### Higher concurrency
All three configs currently use `CONCURRENT_REQUESTS: 1`.
Bumping to 2–3 with `autothrottle: true` is safe for most sites and roughly halves crawl time with no other changes.

### Resume on failure
Checkpoint scraped pages to disk so a crash or timeout mid-crawl can resume from where it stopped
instead of restarting from page 1. Especially valuable for the 37-shard project/project runs.

---

## Polish

- Dark/light theme toggle
- Export run history as CSV
- Per-project run stats chart (items over time)
- Config syntax highlighting in the editor
