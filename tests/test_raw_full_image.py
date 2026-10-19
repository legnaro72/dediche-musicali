import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from scripts.raw_image_handler import process_raw


class FullImageTest(unittest.TestCase):
    def test_every_format_keeps_its_proportions_and_edges(self):
        for size in [(737, 1400), (1600, 700), (900, 900)]:
            with self.subTest(size=size), tempfile.TemporaryDirectory() as folder:
                source = Image.new('RGB', size, 'blue')
                source.paste('red', (0, 0, size[0], 60))
                source.paste('lime', (0, size[1] - 60, size[0], size[1]))
                output = Path(folder) / 'photo.webp'
                with patch('scripts.raw_image_handler.fetch_source_image', return_value=source):
                    self.assertTrue(process_raw({'image': {'source': 'fixture'}}, {}, output, Path(folder) / 'og.webp'))
                with Image.open(output) as result:
                    self.assertAlmostEqual(result.width / result.height, size[0] / size[1], delta=.003)
                    top = result.getpixel((result.width // 2, 10))
                    bottom = result.getpixel((result.width // 2, result.height - 10))
                    self.assertGreater(top[0], 200)
                    self.assertGreater(bottom[1], 200)


if __name__ == '__main__':
    unittest.main()
