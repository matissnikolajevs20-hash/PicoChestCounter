import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from pico_chest_counter import count_delta_matches
from updater import (
    ReleaseInfo,
    UpdateCheckError,
    find_available_update,
    install_update,
    version_tuple,
)


class SpeechMatchingTests(unittest.TestCase):
    def test_counts_each_case_insensitive_whole_word(self):
        self.assertEqual(count_delta_matches("Delta, delta! DELTA"), 3)

    def test_does_not_match_part_of_another_word(self):
        self.assertEqual(count_delta_matches("deltas and alphabet"), 0)


class VersionTests(unittest.TestCase):
    def test_parses_release_versions(self):
        self.assertEqual(version_tuple("v1.2.3"), (1, 2, 3))

    def test_rejects_non_release_tags(self):
        with self.assertRaises(UpdateCheckError):
            version_tuple("latest")


class UpdateDiscoveryTests(unittest.TestCase):
    def test_collects_notes_since_the_installed_version(self):
        releases = [
            {
                "tag_name": "v1.0.2",
                "draft": False,
                "prerelease": False,
                "body": "Second change",
                "assets": [
                    {
                        "name": "PicoChestCounter.zip",
                        "browser_download_url": "https://example.test/latest.zip",
                        "digest": "sha256:" + "a" * 64,
                    }
                ],
            },
            {
                "tag_name": "v1.0.1",
                "draft": False,
                "prerelease": False,
                "body": "First change",
                "assets": [],
            },
            {
                "tag_name": "v2.0.0-beta",
                "draft": False,
                "prerelease": True,
                "body": "Preview",
                "assets": [],
            },
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)
            (app_dir / "app_version.txt").write_text("1.0.0", encoding="utf-8")
            (app_dir / "update-config.json").write_text(
                json.dumps({"repository": "owner/repo"}), encoding="utf-8"
            )
            with patch("updater._request_json", return_value=releases):
                update = find_available_update(app_dir)

        self.assertIsNotNone(update)
        self.assertEqual(update.version, "v1.0.2")
        self.assertIn("v1.0.1\nFirst change", update.notes)
        self.assertIn("v1.0.2\nSecond change", update.notes)
        self.assertNotIn("Preview", update.notes)


class UpdateInstallationTests(unittest.TestCase):
    def test_installs_only_root_app_files_and_checks_digest(self):
        package = io.BytesIO()
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr("pico_chest_counter.py", "print('new')\n")
            archive.writestr("updater.py", "# updated updater\n")
            archive.writestr("app_version.txt", "1.0.1\n")
            archive.writestr("update-config.json", '{"repository":"owner/repo"}')
            archive.writestr("../chest_count.json", '{"count":999}')
        data = package.getvalue()
        release = ReleaseInfo(
            current_version="1.0.0",
            version="v1.0.1",
            notes="Updated",
            download_url="https://example.test/update.zip",
            sha256=hashlib.sha256(data).hexdigest(),
        )
        response = io.BytesIO(data)

        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)
            (app_dir / "chest_count.json").write_text(
                '{"count":7}', encoding="utf-8"
            )
            with patch("updater.urllib.request.urlopen", return_value=response):
                install_update(app_dir, release)

            self.assertEqual(
                (app_dir / "app_version.txt").read_text(encoding="utf-8"),
                "1.0.1\n",
            )
            self.assertEqual(
                (app_dir / "chest_count.json").read_text(encoding="utf-8"),
                '{"count":7}',
            )

    def test_rejects_bad_update_digest(self):
        release = ReleaseInfo(
            current_version="1.0.0",
            version="v1.0.1",
            notes="Updated",
            download_url="https://example.test/update.zip",
            sha256="0" * 64,
        )
        response = io.BytesIO(b"not the expected archive")

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("updater.urllib.request.urlopen", return_value=response):
                with self.assertRaisesRegex(UpdateCheckError, "SHA-256"):
                    install_update(temp_dir, release)


if __name__ == "__main__":
    unittest.main()
