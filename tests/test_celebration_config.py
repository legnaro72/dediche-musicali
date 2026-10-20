import ast
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import Mock
from scripts.celebration_config import normalize_celebration

ROOT = Path(__file__).resolve().parents[1]


class CelebrationConfigTest(unittest.TestCase):
    def test_shared_fixtures_and_unicode_limit(self):
        for case in json.loads((ROOT / 'tests/fixtures/celebration-config.json').read_text(encoding='utf-8')):
            self.assertEqual(normalize_celebration(case['input']), case['expected'])
        self.assertEqual(len(normalize_celebration({'text': '🌺' * 140})['text']), 120)
        self.assertEqual(normalize_celebration({'duration': float('inf')})['duration'], 10)

    def test_existing_streamlit_load_and_save_use_the_same_config_path(self):
        # Exercise the real persistence functions without importing Streamlit/cloud dependencies.
        tree = ast.parse((ROOT / 'scripts/aggiungi_dedica_streamlit.py').read_text(encoding='cp1252'))
        names = {'DEFAULT_SITE_SETTINGS', 'SITE_EFFECT_OPTIONS', 'EFFECT_INTENSITY_OPTIONS', 'SITE_SETTINGS_PATH'}
        nodes = [node for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets)]
        nodes += [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in {'normalize_site_settings', 'save_site_settings'}]
        prime = copy.deepcopy(next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'render_site_configuration'))
        prime.name = 'prime_config_state'
        prime.body = prime.body[:next(i for i, node in enumerate(prime.body) if isinstance(node, ast.FunctionDef) and node.name == 'mark_site_config_dirty')]
        nodes.append(prime)
        namespace = {'normalize_celebration': normalize_celebration, 'normalize_effect_intensity': lambda value, *args: value,
                     'normalize_site_lock_image_path': lambda value: value, 'read_github_json': Mock(return_value=({}, 'sha')), 'write_github_json': Mock()}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<settings>', 'exec'), namespace)
        ui = Mock()
        ui.session_state = {'config_loaded_version': 'default'}
        namespace['st'] = ui
        namespace['prime_config_state']()
        self.assertEqual(ui.session_state['config_celebration_duration'], 10)
        self.assertFalse(ui.session_state['config_celebration_enabled'])
        legacy = namespace['normalize_site_settings']({'buttons': {'plusVote': False}})
        self.assertEqual(legacy['celebration'], {'enabled': False, 'text': '', 'duration': 10})
        self.assertFalse(legacy['buttons']['plusVote'])
        legacy['celebration'] = {'enabled': True, 'text': "Pìlli, l’amore!", 'duration': 999}
        namespace['save_site_settings'](legacy, 'Test only')
        args = namespace['write_github_json'].call_args.args
        self.assertEqual(args[0], 'public/config/site-settings.json')
        self.assertEqual(args[1]['celebration']['duration'], 30)
        self.assertEqual(args[1]['celebration']['text'], "Pìlli, l’amore!")


if __name__ == '__main__':
    unittest.main()
