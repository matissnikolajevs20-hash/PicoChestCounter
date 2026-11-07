import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from pico_chest_counter import DeltaChestCounter, count_delta_matches
import updater
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

    def test_installed_app_prefers_the_windows_installer_asset(self):
        release = {
            "tag_name": "v1.0.1",
            "draft": False,
            "prerelease": False,
            "body": "Branded installer",
            "assets": [
                {
                    "name": "PicoChestCounter.zip",
                    "browser_download_url": "https://example.test/source.zip",
                },
                {
                    "name": "PicoChestCounter-Setup.exe",
                    "browser_download_url": "https://example.test/setup.exe",
                },
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)
            (app_dir / "app_version.txt").write_text("1.0.0", encoding="utf-8")
            (app_dir / "update-config.json").write_text(
                json.dumps({"repository": "owner/repo"}), encoding="utf-8"
            )
            with (
                patch.object(updater.sys, "frozen", True, create=True),
                patch("updater._request_json", return_value=[release]),
            ):
                update = find_available_update(app_dir)

        self.assertIsNotNone(update)
        self.assertEqual(update.download_url, "https://example.test/setup.exe")


class UpdateInstallationTests(unittest.TestCase):
    def test_frozen_app_starts_downloaded_installer_handoff(self):
        release = ReleaseInfo(
            current_version="1.0.0",
            version="v1.0.1",
            notes="Branded installer",
            download_url="https://example.test/setup.exe",
            sha256=hashlib.sha256(b"installer").hexdigest(),
        )
        response = io.BytesIO(b"installer")
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch.object(updater.sys, "frozen", True, create=True),
                patch("updater.tempfile.gettempdir", return_value=temp_dir),
                patch("updater.subprocess.Popen") as popen,
                patch("updater.urllib.request.urlopen", return_value=response),
            ):
                install_update(temp_dir, release)

            popen.assert_called_once()
            command_script = Path(popen.call_args.args[0][-1])
            self.assertTrue(command_script.exists())
            self.assertIn(
                "/SILENT /SUPPRESSMSGBOXES /NORESTART",
                command_script.read_text(encoding="utf-8"),
            )

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


class UpdatePromptTests(unittest.TestCase):
    def test_yes_starts_installing_the_available_update(self):
        app = DeltaChestCounter.__new__(DeltaChestCounter)
        app.root = MagicMock()
        app.update_dialog = None
        dialog = MagicMock()
        dialog.winfo_exists.return_value = False
        buttons = []

        def make_button(*args, **kwargs):
            button = MagicMock()
            button.text = kwargs["text"]
            button.command = kwargs["command"]
            buttons.append(button)
            return button

        release = ReleaseInfo(
            current_version="1.0.0",
            version="v1.0.1",
            notes="Updated",
            download_url="https://example.test/update.zip",
            sha256=None,
        )
        with (
            patch("pico_chest_counter.tk.Toplevel", return_value=dialog),
            patch("pico_chest_counter.tk.Label"),
            patch("pico_chest_counter.tk.Text"),
            patch("pico_chest_counter.tk.Frame"),
            patch("pico_chest_counter.ttk.Button", side_effect=make_button),
            patch.object(app, "confirm_update") as confirm_update,
        ):
            app.show_update_dialog(release)
            yes_button = next(button for button in buttons if button.text == "Yes")
            yes_button.command()
            confirm_update.assert_called_once_with(dialog, release)


if __name__ == "__main__":
    unittest.main()
