import json
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import publish_daily, sync_from_google_sheet, utils


def make_dedication(date_str, status):
    return {
        'id': f'ded-{date_str}',
        'date': date_str,
        'day_name': '',
        'status': status,
        'song_title': f'Song {date_str}',
        'artist': 'Artist',
        'dedication_title': f'Title {date_str}',
        'dedication_text': f'Text {date_str}',
        'audio': {'url': 'https://example.com/audio', 'type': 'other'},
        'vote': {'url': 'https://example.com/vote'},
        'image': {'path': f'/images/dedications/{date_str}.webp', 'alt': 'Alt', 'mode': 'none', 'source': ''},
        'short_phrase': '',
        'tags': [],
        'seo': {'title': 'SEO', 'description': 'Description'},
        'created_at': '2026-05-10T00:00:00+02:00',
        'updated_at': '2026-05-10T00:00:00+02:00',
    }


def make_row(date_str, status):
    ded = make_dedication(date_str, status)
    return {
        'id': ded['id'],
        'date': date_str,
        'status': status,
        'song_title': ded['song_title'],
        'artist': ded['artist'],
        'dedication_title': ded['dedication_title'],
        'dedication_text': ded['dedication_text'],
        'audio_url': ded['audio']['url'],
        'audio_type': ded['audio']['type'],
        'vote_url': ded['vote']['url'],
        'image_mode': ded['image']['mode'],
        'image_source': '',
        'short_phrase': '',
        'tags': '',
        'seo_title': '',
        'seo_description': '',
        'image_alt': '',
    }


class AppendOnlyPublishTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data_dir = self.root / 'data' / 'dedications'
        self.data_dir.mkdir(parents=True)

        patches = [
            patch.object(utils, 'ROOT_DIR', self.root),
            patch.object(utils, 'DATA_DIR', self.data_dir),
        ]
        self.patchers = patches
        for patcher in patches:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.tmp.cleanup()

    def write_dedication(self, date_str, status):
        path = self.data_dir / f'{date_str}.json'
        path.write_text(json.dumps(make_dedication(date_str, status)), encoding='utf-8')

    def read_dedication(self, date_str):
        return json.loads((self.data_dir / f'{date_str}.json').read_text(encoding='utf-8'))

    def test_wednesday_publish_preserves_monday_and_tuesday_archive(self):
        self.write_dedication('2026-05-11', 'published')
        self.write_dedication('2026-05-12', 'published')
        self.write_dedication('2026-05-13', 'scheduled')

        tuesday_before = self.read_dedication('2026-05-12')
        rows = [
            make_row('2026-05-11', 'published'),
            make_row('2026-05-12', 'published'),
            make_row('2026-05-13', 'scheduled'),
        ]

        sync_ok = sync_from_google_sheet.sync_rows(
            rows,
            default_vote_url='https://example.com/vote',
            target_date='2026-05-13',
        )
        self.assertTrue(sync_ok)

        fake_generate = types.ModuleType('scripts.generate_image')
        fake_generate.ensure_fonts = lambda: {}
        fake_generate.generate_for_dedication = lambda ded, fonts, dry_run=False: True

        with patch.dict(sys.modules, {'scripts.generate_image': fake_generate}):
            publish_ok = publish_daily.publish('2026-05-13')

        self.assertTrue(publish_ok)
        self.assertEqual(self.read_dedication('2026-05-11')['status'], 'published')
        self.assertEqual(self.read_dedication('2026-05-12'), tuesday_before)
        self.assertEqual(self.read_dedication('2026-05-13')['status'], 'published')
        self.assertTrue((self.data_dir / '2026-05-11.json').exists())
        self.assertTrue((self.data_dir / '2026-05-12.json').exists())
        self.assertTrue((self.data_dir / '2026-05-13.json').exists())

    def test_sync_does_not_overwrite_published_without_force(self):
        self.write_dedication('2026-05-12', 'published')
        before = self.read_dedication('2026-05-12')

        row = make_row('2026-05-12', 'scheduled')
        row['song_title'] = 'Changed in sheet'

        sync_ok = sync_from_google_sheet.sync_rows(
            [row],
            default_vote_url='https://example.com/vote',
        )

        self.assertTrue(sync_ok)
        self.assertEqual(self.read_dedication('2026-05-12'), before)

    def test_publish_all_dedications_for_same_date(self):
        first = make_dedication('2026-05-14', 'scheduled')
        first['id'] = '2026-05-14-first-song'
        second = make_dedication('2026-05-14', 'scheduled')
        second['id'] = '2026-05-14-second-song'
        (self.data_dir / f"{first['id']}.json").write_text(json.dumps(first), encoding='utf-8')
        (self.data_dir / f"{second['id']}.json").write_text(json.dumps(second), encoding='utf-8')

        fake_generate = types.ModuleType('scripts.generate_image')
        fake_generate.ensure_fonts = lambda: {}
        fake_generate.generate_for_dedication = lambda ded, fonts, dry_run=False: True

        with patch.dict(sys.modules, {'scripts.generate_image': fake_generate}):
            publish_ok = publish_daily.publish('2026-05-14')

        self.assertTrue(publish_ok)
        first_after = json.loads((self.data_dir / f"{first['id']}.json").read_text(encoding='utf-8'))
        second_after = json.loads((self.data_dir / f"{second['id']}.json").read_text(encoding='utf-8'))
        self.assertEqual(first_after['status'], 'published')
        self.assertEqual(second_after['status'], 'published')
        self.assertEqual(first_after['image']['path'], '/images/dedications/2026-05-14-first-song.webp')
        self.assertEqual(second_after['image']['path'], '/images/dedications/2026-05-14-second-song.webp')

    def test_publish_can_target_one_dedication_for_same_date(self):
        first = make_dedication('2026-05-15', 'scheduled')
        first['id'] = '2026-05-15-first-song'
        second = make_dedication('2026-05-15', 'scheduled')
        second['id'] = '2026-05-15-second-song'
        (self.data_dir / f"{first['id']}.json").write_text(json.dumps(first), encoding='utf-8')
        (self.data_dir / f"{second['id']}.json").write_text(json.dumps(second), encoding='utf-8')

        fake_generate = types.ModuleType('scripts.generate_image')
        fake_generate.ensure_fonts = lambda: {}
        fake_generate.generate_for_dedication = lambda ded, fonts, dry_run=False: True

        with patch.dict(sys.modules, {'scripts.generate_image': fake_generate}):
            publish_ok = publish_daily.publish('2026-05-15', target_id=first['id'])

        self.assertTrue(publish_ok)
        first_after = json.loads((self.data_dir / f"{first['id']}.json").read_text(encoding='utf-8'))
        second_after = json.loads((self.data_dir / f"{second['id']}.json").read_text(encoding='utf-8'))
        self.assertEqual(first_after['status'], 'published')
        self.assertEqual(second_after['status'], 'scheduled')


if __name__ == '__main__':
    unittest.main()
