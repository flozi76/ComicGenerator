"""Generate background music for the comic reel using fal.ai stable-audio."""
import asyncio
from pathlib import Path

from src.agents.plot_agent import PlotResult

_STYLE_MOODS: dict[str, str] = {
    "dylan-dog":  "dark horror noir, slow suspenseful strings, ominous piano, cinematic dread",
    "hugo-pratt": "mediterranean adventure jazz, nostalgic brass, old film score, melancholic",
    "magnus":     "dark thriller, pulsing low strings, noir detective atmosphere, brooding",
    "manga":      "anime action score, intense orchestral, dramatic taiko drums, energetic",
    "enki-bilal": "sci-fi dystopia, cold electronic ambiance, eerie synthesizers, haunting",
    "milo-manara":"romantic European cinema, sensual strings, Italian 70s film score, lush",
}

_DEFAULT_MOOD = "cinematic atmospheric, evocative, instrumental, dramatic, no vocals"

# stable-audio-3 medium hard cap on generation length (~6m20s)
_MAX_SECONDS = 380.0


def _build_prompt(plot: PlotResult, style_name: str) -> str:
    mood = _STYLE_MOODS.get(style_name, _DEFAULT_MOOD)
    return f"{mood}, instrumental, no vocals — {plot.title}: {plot.tagline}"


async def generate_music(
    plot: PlotResult,
    style_name: str,
    duration: float,
    api_key: str,
    output_dir: Path,
    model: str = "fal-ai/stable-audio-3/medium/text-to-audio",
) -> Path:
    """Generate story-aligned background music via fal.ai and save to output_dir/music.wav.

    Audio is capped at _MAX_SECONDS; the caller should loop it in ffmpeg for longer videos.
    """
    if not api_key:
        raise RuntimeError(
            "fal.api_key is required for music generation. Set it in config.yml."
        )
    import httpx

    prompt = _build_prompt(plot, style_name)
    seconds = min(duration, _MAX_SECONDS)
    print(f"      Music prompt  : {prompt[:90]}...")
    print(f"      Music duration: {seconds:.0f}s")

    headers = {
        "Authorization": f"Key {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"prompt": prompt, "duration": seconds, "output_format": "wav"}

    async with httpx.AsyncClient(timeout=120) as http:
        resp = await http.post(
            f"https://queue.fal.run/{model}",
            headers=headers,
            json=payload,
        )
        try:
            resp.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"fal music submit error: {e} — {resp.text}") from e

        submit = resp.json()
        status_url = submit["status_url"]
        response_url = submit["response_url"]

        for _ in range(60):
            await asyncio.sleep(2)
            poll = await http.get(status_url, headers=headers)
            poll.raise_for_status()
            status = poll.json().get("status", "")

            if status == "COMPLETED":
                result = await http.get(response_url, headers=headers)
                result.raise_for_status()
                data = result.json()
                audio_url = data["audio"]["url"]
                audio_resp = await http.get(audio_url, timeout=60)
                audio_resp.raise_for_status()
                music_path = output_dir / "music.wav"
                music_path.write_bytes(audio_resp.content)
                print(f"      Music saved   → {music_path}")
                return music_path

            if status not in ("IN_QUEUE", "IN_PROGRESS"):
                raise RuntimeError(f"fal music generation failed: status={status!r}")

    raise RuntimeError("fal music generation timed out after 120 seconds.")
