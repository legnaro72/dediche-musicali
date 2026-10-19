"""Audit raw archive photos against local originals; --write restores cropped files."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]


def audit(write=False):
    report = {"checked": 0, "cropped": [], "unavailable": []}
    for file in sorted((ROOT / 'data/dedications').glob('*.json')):
        dedication = json.loads(file.read_text(encoding='utf-8'))
        photo = dedication.get('image') or {}
        if not isinstance(photo, dict) or photo.get('mode', dedication.get('image_mode')) != 'raw':
            continue
        source = (ROOT / photo.get('source', '')).resolve()
        target = (ROOT / 'public' / photo.get('path', '').lstrip('/')).resolve()
        if not source.is_relative_to(ROOT) or not target.is_relative_to(ROOT / 'public'):
            report['unavailable'].append(dedication['id'])
            continue
        if not source.is_file() or not target.is_file() or source == target:
            report['unavailable'].append(dedication['id'])
            continue
        with Image.open(source) as original, Image.open(target) as rendered:
            full = ImageOps.exif_transpose(original).convert('RGB')
            report['checked'] += 1
            if abs((full.width / full.height) / (rendered.width / rendered.height) - 1) <= .005:
                continue
            report['cropped'].append({'id': dedication['id'], 'original': list(full.size), 'published': list(rendered.size)})
            if write:
                full.thumbnail((1200, 1800), Image.Resampling.LANCZOS)
                full.save(target, 'WEBP', quality=84, method=6)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    print(json.dumps(audit(parser.parse_args().write), indent=2))
