# AAQ docs

Source for [docs.ask-a-question.com](https://docs.ask-a-question.com), built with
MkDocs Material. This folder is a standalone [uv](https://docs.astral.sh/uv/)
project, so you don't need the backend's dependencies to work on it.

## Run locally

```bash
cd docs
uv run mkdocs serve
```

Then open <http://127.0.0.1:8000>. `uv run` creates the virtualenv and installs
the pinned deps on first use.

## Layout

- `mkdocs.yml` – site config and navigation
- `docs/` – Markdown pages, images, and stylesheets
- `pyproject.toml` / `uv.lock` – pinned MkDocs dependencies

Some pages embed files from elsewhere in the repo (e.g. the env templates in
`deployment/docker-compose/`) via `--8<--` snippets. Those paths are resolved
from the repo root.

## Build

```bash
uv run mkdocs build --strict   # outputs to docs/site/
```

Versioned deploys to GitHub Pages run through `mike` in
`.github/workflows/docs.yaml`.
