#!/usr/bin/env python3
"""Interactive Instagram login — run this once to clear the new-device
verification challenge and cache the session to `instagram_session.json`.

After this succeeds, the comic generator can publish without re-prompting.

    python3 scripts/instagram_login.py
    python3 scripts/instagram_login.py --config /path/to/config.yml
"""
import argparse
import sys
from pathlib import Path

# allow running directly from the project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_config
from src.publisher import login


def main() -> None:
    parser = argparse.ArgumentParser(description="Log in to Instagram and cache the session.")
    parser.add_argument("--config", default="config.yml", help="Path to config YAML.")
    args = parser.parse_args()

    cfg = load_config(Path(args.config)).instagram
    print(f"Logging in as {cfg.username} ...")
    client = login(cfg)
    me = client.account_info()
    print(f"Logged in as @{me.username} ({me.full_name}).")
    print(f"Session cached to {cfg.session_file}. You can now publish from the generator.")


if __name__ == "__main__":
    main()
