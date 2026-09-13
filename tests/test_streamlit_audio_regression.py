import sys
import types
import unittest
from unittest.mock import Mock, patch


def install_streamlit_stub():
    streamlit = types.ModuleType("streamlit")
    streamlit.secrets = {}
    streamlit.cache_data = lambda *args, **kwargs: (lambda func: func)
    streamlit.cache_resource = lambda *args, **kwargs: (lambda func: func)

    components = types.ModuleType("streamlit.components")
    components_v1 = types.ModuleType("streamlit.components.v1")
    components.v1 = components_v1

    sys.modules.setdefault("streamlit", streamlit)
    sys.modules.setdefault("streamlit.components", components)
    sys.modules.setdefault("streamlit.components.v1", components_v1)


install_streamlit_stub()

from scripts.aggiungi_dedica_streamlit import default_form_values, prepare_values, fetch_spotify_track_metadata


class StreamlitAudioRegressionTest(unittest.TestCase):
    def test_spotify_artist_from_description_when_oembed_has_only_title(self):
        for description in (
            "Ivano Fossati \u00b7 La Mia Banda Suona Il Rock \u00b7 Brano \u00b7 1979",
            "Listen to La mia banda suona il rock on Spotify. Song \u00b7 Ivano Fossati \u00b7 1979",
        ):
            with self.subTest(description=description):
                oembed = Mock(status_code=200)
                oembed.json.return_value = {"title": "La mia banda suona il rock"}
                page = Mock(status_code=200, text=(
                    '<meta property="og:title" content="La mia banda suona il rock"/>'
                    f'<meta property="og:description" content="{description}"/>'
                ))
                with patch("scripts.aggiungi_dedica_streamlit.requests.get", side_effect=[oembed, page]):
                    result = fetch_spotify_track_metadata(
                        "https://open.spotify.com/track/6fB3Wy1x9EdhfFwqy8lJcZ?si=test"
                    )
                self.assertEqual(result, {"song_title": "La mia banda suona il rock", "artist": "Ivano Fossati"})

    def test_spotify_url_wins_over_stale_uploaded_audio_state(self):
        values = default_form_values()
        values.update(
            {
                "date": "2026-09-14",
                "song_title": "Test Song",
                "artist": "Test Artist",
                "audio_url": "https://open.spotify.com/intl-it/track/0xYlLcTvwe9Odc2R7Ftdkk?si=abc",
                "source_type": "uploaded_audio",
                "mime_type": "audio/mpeg",
                "original_filename": "old-upload.mp3",
                "image_mode": "none",
            }
        )

        cleaned = prepare_values(values)

        self.assertEqual(cleaned["source_type"], "spotify")
        self.assertEqual(cleaned["audio_type"], "spotify")
        self.assertEqual(cleaned["audio_url"], "https://open.spotify.com/track/0xYlLcTvwe9Odc2R7Ftdkk")
        self.assertEqual(cleaned["mime_type"], "")
        self.assertEqual(cleaned["original_filename"], "")

    def test_manual_id_is_safe_for_github_upload_path(self):
        values = default_form_values()
        values.update(
            {
                "id": "2026/09/14 Dedica Speciale",
                "date": "2026-09-14",
                "song_title": "Test Song",
                "artist": "Test Artist",
                "audio_url": "https://open.spotify.com/track/0xYlLcTvwe9Odc2R7Ftdkk",
                "image_mode": "raw",
                "image_source": "public/images/upload/existing.webp",
            }
        )

        cleaned = prepare_values(values)

        self.assertEqual(cleaned["id"], "2026-09-14-dedica-speciale")


if __name__ == "__main__":
    unittest.main()
