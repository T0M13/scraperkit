# Admin Panel

The admin panel is a browser-based dashboard for managing projects, starting crawls, and monitoring runs in real time.

## Starting

```bash
scraperkit serve
# or with options:
scraperkit serve --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`.

---

## Panels

### Overview

The landing page. Shows:
- **Stats** — total runs, successful, failed, active projects, live jobs
- **Projects table** — every project with run count, last run time, last status, and a quick "Run" button
- **Recent runs** — last 8 runs, clickable to open step detail

### Live Jobs

Shows all jobs started in this server session.

- Live status badge (queued → running → success/failed)
- PID of the subprocess
- **Console** button — opens a live log stream for that job. Log lines are coloured by content (errors in red, warnings in yellow, success in green, ScraperKit messages in blue)
- **Cancel** button — sends SIGTERM to the subprocess
- Auto-scroll toggle — locks the console at its current position so you can read without it jumping

The console uses **Server-Sent Events** — the browser keeps a persistent HTTP connection open and receives log lines in real time as the subprocess writes them to stdout.

### Run History

All runs stored in the SQLite database.

- Filter by project name (type to filter instantly)
- Click any row or "Details" to open the step drawer
- Step drawer shows: project, status, started, duration, item count, and for every step: status badge, duration, items in/out, error message

### Configs

Create and manage project YAML config files stored in the `configs/` folder.

- **Edit** — opens the YAML editor inline
- **Run** — starts the crawl immediately and redirects to Live Jobs with console open
- **Delete** — removes the file

The editor has a **Validate** button that calls the API to parse and validate your YAML against the Pydantic schema before saving.

### New Crawl

Two ways to start a crawl:

**Quick Start** — pick a saved config from the dropdown and click Run.

**Advanced** — paste or write raw YAML in the editor. Validate it first, then click "Run This Config". The config is sent inline to the API, run immediately, and you're redirected to the live console.

---

## API endpoints

The admin panel is backed by a FastAPI app. You can use the API directly too.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/projects` | List all projects |
| `GET` | `/api/runs` | List runs (`?project=name&limit=50`) |
| `GET` | `/api/runs/{id}` | Run detail with steps |
| `GET` | `/api/projects/{name}/stats` | Aggregate stats for a project |
| `GET` | `/api/jobs` | List all jobs (current server session) |
| `POST` | `/api/jobs` | Start a job |
| `DELETE` | `/api/jobs/{id}` | Cancel a running job |
| `GET` | `/api/jobs/{id}/logs/stream` | SSE log stream |
| `GET` | `/api/configs` | List config files |
| `GET` | `/api/configs/{name}` | Read a config |
| `POST` | `/api/configs` | Create a config |
| `PUT` | `/api/configs/{name}` | Update a config |
| `DELETE` | `/api/configs/{name}` | Delete a config |
| `POST` | `/api/configs/validate` | Validate YAML content |

Full interactive docs at `http://localhost:8000/docs` (Swagger UI).

### Starting a job via API

```bash
# From a saved config file
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"config_name": "my_project"}'

# From a file path
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"config_path": "/path/to/project.yaml"}'

# Inline YAML
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"inline_config": "name: test\nstart_urls: [https://example.com]\nworkflow: [crawl, export_json]"}'
```

Response:
```json
{"run_id": "a1b2c3d4", "project": "my_project", "status": "running"}
```

### Streaming logs via curl

```bash
curl -N http://localhost:8000/api/jobs/a1b2c3d4/logs/stream
```

---

## Running on a server

To expose the panel on a server:

```bash
scraperkit serve --host 0.0.0.0 --port 8000
```

For production, put nginx in front:

```nginx
server {
    listen 80;
    server_name scraperkit.internal;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # Required for SSE (log streaming)
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
        chunked_transfer_encoding on;
    }
}
```

The `proxy_buffering off` line is critical — without it, Nginx buffers the SSE stream and the live console won't work.

---

## Configs directory

By default, configs are stored in `./configs/` relative to your working directory.

Override with an env var:
```bash
SCRAPERKIT_CONFIGS=/etc/scraperkit/configs scraperkit serve
```

You can also put existing YAML files in the `configs/` folder manually — they'll appear in the panel immediately.
