import re

def extract_quality(text: str) -> str:
    if not text:
        return "UNKNOWN"

    t = text.lower()

    # common qualities
    if "2160p" in t or "4k" in t:
        return "2160p"
    if "1080p" in t:
        return "1080p"
    if "720p" in t:
        return "720p"
    if "480p" in t:
        return "480p"
    if "360p" in t:
        return "360p"

    # fallback regex
    m = re.search(r'(\d{3,4})p', t)
    if m:
        return f"{m.group(1)}p"

    return "UNKNOWN"
