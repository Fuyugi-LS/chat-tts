import configparser
import re
from pathlib import Path

_DEFAULTS = {
    "youtube_video_id": "",
    "delay_per_char": "0.03",
    "max_delay": "2.0",
}


def load(envp: dict) -> configparser.ConfigParser:
    Path(envp["TT2S_LOGS"]).mkdir(parents=True, exist_ok=True)
    cfg = configparser.ConfigParser()
    cfg["settings"] = _DEFAULTS.copy()
    return cfg


def extract_video_id(raw: str) -> str:
    if not raw or "http" not in raw:
        return raw.strip()
    for pat in [
        r"v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"live/([a-zA-Z0-9_-]{11})",
    ]:
        m = re.search(pat, raw)
        if m:
            return m.group(1)
    return raw.strip()
