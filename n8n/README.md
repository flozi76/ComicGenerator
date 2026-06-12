# n8n integration

Phased migration of the pipeline to n8n — see `Notes/n8n-workflow-plan.md` for the
full node-by-node plan. This directory holds the importable workflows.

## Phase 0 — CLI wrapper (`phase0-workflow.json`)

One Execute Command node runs the existing Python CLI on a schedule:

```
Manual / Schedule trigger → Pick idea (Code) → Generate & publish (Execute Command)
                                                └─ scripts/n8n_generate.sh "<idea>" <style>
                                                   └─ python3 -m src.main --idea … --publish
```

### Prerequisites (all already true for local dev)

- This repo at `/Users/florianzimmermann/Development/Claude/ComicGenerator` with a
  filled `config.yml` (API keys, `tiktok.enabled: true`, inbox mode token cached
  in `tiktok_token.json`)
- `python3` with `requirements.txt` installed, `ffmpeg` on PATH (brew)
- Node.js ≥ 20

### Setup

```bash
npm install -g n8n      # or: brew install n8n
n8n                     # starts the UI at http://localhost:5678
```

1. In the n8n UI: **Workflows → Import from File** → `n8n/phase0-workflow.json`.
2. Open the **Pick idea** node to edit the idea pool / style. If the repo lives
   elsewhere, fix `projectDir` there too.
3. Click **Execute workflow** (uses the manual trigger) for a test run — the
   Execute Command node streams the CLI output into the execution log. A full run
   takes a few minutes.
4. Toggle the workflow **Active** to enable the daily 19:00 schedule.

### Notes

- The schedule only fires while n8n itself is running — keep it running (or add
  it to launchd/pm2) for unattended daily posts.
- The reel lands in **TikTok drafts** (inbox mode): finish caption/hashtags and
  post from the TikTok app.
- A non-zero exit from the CLI fails the node, so errors are visible in n8n's
  execution list; generation output stays in `output/<date>/story_*/` either way.
