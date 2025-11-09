from datetime import datetime, timezone, timedelta
import re

# e.g., "20s", "5m", "1h30m", "2d3h", "90m", "  2h  "
DELAY_RE = re.compile(r"(?i)^\s*(?:(\d+)\s*d)?\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?\s*(?:(\d+)\s*s)?\s*$")

def parse_delay_to_seconds(s: str) -> int:
    """
    Parse delay strings like '20s', '5m', '1h30m', '2d3h', '90m'.
    Returns total seconds (int). Raises ValueError on bad input or zero.
    """
    if not s:
        raise ValueError("delay string is empty")
    m = DELAY_RE.match(s)
    if not m:
        raise ValueError(f"Invalid delay format: {s!r}")
    d, h, m_, s_ = m.groups()
    total = 0
    if d:  total += int(d) * 86400
    if h:  total += int(h) * 3600
    if m_: total += int(m_) * 60
    if s_: total += int(s_)
    if total <= 0:
        raise ValueError("delay must be > 0 seconds")
    return total

def now_iso() -> str:
    """UTC timestamp like '2025-11-06T09:12:34.123456Z'."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def iso_in_utc_from_seconds_from_now(seconds: int) -> str:
    """Return UTC ISO time `seconds` from now, with 'Z' suffix."""
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")
