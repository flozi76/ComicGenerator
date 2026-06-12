#!/usr/bin/env bash
# Phase 0 n8n wrapper: generate a comic and publish it to TikTok drafts.
#
# Called by the n8n Execute Command node (see n8n/phase0-workflow.json):
#     bash scripts/n8n_generate.sh "<idea>" [style]
#
# Runs the existing CLI non-interactively (--publish skips the y/N prompt).
set -euo pipefail

# n8n may run with a minimal PATH (launchd/service); make sure brew's
# ffmpeg and python3 are found.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

cd "$(dirname "$0")/.."

IDEA="${1:?usage: n8n_generate.sh \"<idea>\" [style]}"
STYLE="${2:-dylan-dog}"

echo "=== ComicGenerator n8n run $(date '+%Y-%m-%d %H:%M:%S') ==="
echo "idea : $IDEA"
echo "style: $STYLE"

exec python3 -m src.main --idea "$IDEA" --style "$STYLE" --publish
