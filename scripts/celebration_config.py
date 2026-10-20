"""Validation shared by Streamlit loading and saving; old settings stay disabled."""
import math

CELEBRATION_TEXT_LIMIT = 120


def normalize_celebration(value):
    raw = value if isinstance(value, dict) else {}
    text = raw.get('text', '')
    text = ' '.join(text.split())[:CELEBRATION_TEXT_LIMIT] if isinstance(text, str) else ''
    duration = raw.get('duration', 10)
    try:
        duration = float(duration) if not isinstance(duration, bool) else 10
        duration = int(duration) if math.isfinite(duration) else 10
    except (TypeError, ValueError, OverflowError):
        duration = 10
    return {'enabled': raw.get('enabled') is True and bool(text), 'text': text,
            'duration': max(3, min(30, duration))}
