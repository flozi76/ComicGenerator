# n8n + ffmpeg (reel rendering) + python3 (Phase 0 CLI path & TikTok token helper).
#
# Not based on n8nio/n8n: that image is hardened (no apk/package manager), so
# ffmpeg/python can't be added to it. Instead: node:22-alpine + `npm i -g n8n`,
# the npm install route from n8n's docs.
#
# Build/run via docker-compose.yml in this directory.
FROM node:22-alpine

RUN apk add --no-cache ffmpeg python3 py3-pip py3-pillow py3-yaml py3-requests tzdata bash

RUN npm install -g --omit=dev n8n && npm cache clean --force

# Python deps for the Phase 0 CLI path. The legacy Instagram path (instagrapi)
# is intentionally skipped — it is disabled by default and heavy to build on Alpine.
RUN pip3 install --break-system-packages --no-cache-dir \
    openai anthropic httpx python-slugify

RUN mkdir -p /home/node/.n8n && chown -R node:node /home/node
USER node
WORKDIR /home/node
EXPOSE 5678
ENTRYPOINT ["n8n"]
