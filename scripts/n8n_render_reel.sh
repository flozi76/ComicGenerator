#!/usr/bin/env bash
# Render scene_*.png (+ optional music.wav) in a run directory into a 9:16
# panel reel, mirroring src/publisher.build_panel_reel: every frame spans the
# full 1080px width (never cropped horizontally), vertically center-cropped or
# black-padded to 1920px.
#
# Called by the native n8n workflow's Execute Command node:
#     n8n_render_reel.sh <dir> [panel_seconds]
# Prints a single JSON line on success: {"reel": "<path>", "size": <bytes>}
set -euo pipefail

DIR="${1:?usage: n8n_render_reel.sh <dir> [panel_seconds]}"
SECS="${2:-3}"

cd "$DIR"
shopt -s nullglob
frames=(scene_*.png)
if [ "${#frames[@]}" -eq 0 ]; then
  echo "no scene_*.png files in $DIR" >&2
  exit 1
fi

# concat demuxer list; the last frame is repeated because the demuxer ignores
# the final duration directive.
: > frames.txt
for f in "${frames[@]}"; do
  printf "file '%s'\nduration %s\n" "$f" "$SECS" >> frames.txt
done
printf "file '%s'\n" "${frames[${#frames[@]}-1]}" >> frames.txt

VF="scale=1080:-2,crop=1080:'min(ih,1920)':0:'(ih-min(ih,1920))/2',pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,format=yuv420p"

if [ -f music.wav ]; then
  fade_start=$(awk "BEGIN { d = ${#frames[@]} * $SECS - 2; print (d > 0 ? d : 0) }")
  ffmpeg -y -loglevel error \
    -f concat -safe 0 -i frames.txt \
    -stream_loop -1 -i music.wav -shortest \
    -vf "$VF" -af "afade=t=out:st=${fade_start}:d=2" \
    -r 30 -c:v libx264 -c:a aac -movflags +faststart reel.mp4
else
  ffmpeg -y -loglevel error \
    -f concat -safe 0 -i frames.txt \
    -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 -shortest \
    -vf "$VF" \
    -r 30 -c:v libx264 -c:a aac -movflags +faststart reel.mp4
fi

size=$(wc -c < reel.mp4 | tr -d ' ')
echo "{\"reel\": \"$DIR/reel.mp4\", \"size\": $size}"
