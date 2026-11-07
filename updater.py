import hashlib
import json
import os
import re
import shutil
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

APP_FILES = {
    "pico_chest_counter.py",
    "updater.py",
    "app_version.txt",
    "update-config.json",
    "requirements.txt",
    "setup.bat",
    "setup.ps1",
    "run.bat",
    "share.bat",
    "share.ps1",
    "README.md",
}
RELEASE_ASSET = "PicoChestCounter.zip"
RELEASE_API_TIMEOUT = 8
DOWNLOAD_TIMEOUT = 60


class UpdateCheckError(Exception):
    pass


class UpdateNotConfiguredError(UpdateCheckError):
    pass


@dataclass(frozen=True)
class ReleaseInfo:
    current_version: str
    version: str
    notes: str
    download_url: str
    sha256: str | None


def version_tuple(version):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise UpdateCheckError(f"Invalid app version: {version}")
    return tuple(int(part) for part in match.groups())


def _read_repository(app_dir):
    config_path = app_dir / "update-config.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise UpdateCheckError(f"Could not read update-config.json: {error}") from error
    if not isinstance(config, dict):
        raise UpdateCheckError("update-config.json must contain a JSON object.")

    repository = config.get("repository", "")
    if not isinstance(repository, str):
        raise UpdateCheckError("The repository setting must be a string.")
    repository = repository.strip()
    if not repository:
        raise UpdateNotConfiguredError(
            "Automatic updates are not configured for this copy of the app."
        )
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise UpdateCheckError(
            "update-config.json must contain a GitHub owner/repository."
        )
    return repository


def _read_current_version(app_dir):
    try:
        return (app_dir / "app_version.txt").read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError) as error:
        raise UpdateCheckError(f"Could not read app_version.txt: {error}") from error


def _request_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "PicoChestCounter",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=RELEASE_API_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except (
        urllib.error.URLError,
        TimeoutError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        raise UpdateCheckError(f"Could not check GitHub Releases: {error}") from error


def find_available_update(app_dir):
    app_dir = Path(app_dir)
    repository = _read_repository(app_dir)
    current_version = _read_current_version(app_dir)
    current = version_tuple(current_version)
    releases = _request_json(
        f"https://api.github.com/repos/{repository}/releases?per_page=100"
    )
    if not isinstance(releases, list):
        raise UpdateCheckError("GitHub returned an invalid release list.")

    published = []
    for release in releases:
        if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
            continue
        tag = release.get("tag_name", "")
        try:
            version = version_tuple(tag)
        except UpdateCheckError:
            continue
        if version > current:
            published.append((version, tag, release))

    if not published:
        return None

    published.sort(key=lambda item: item[0])
    _, latest_tag, latest_release = published[-1]
    latest_assets = latest_release.get("assets", [])
    if not isinstance(latest_assets, list):
        raise UpdateCheckError(f"Release {latest_tag} has an invalid asset list.")
    asset = next(
        (
            item
            for item in latest_assets
            if isinstance(item, dict) and item.get("name") == RELEASE_ASSET
        ),
        None,
    )
    if asset is None:
        raise UpdateCheckError(
            f"Release {latest_tag} is missing the {RELEASE_ASSET} asset."
        )
    download_url = asset.get("browser_download_url", "")
    if not isinstance(download_url, str) or not download_url.startswith("https://"):
        raise UpdateCheckError("The release asset does not have a secure download URL.")

    notes = []
    for _, tag, release in published:
        body = release.get("body", "")
        if not isinstance(body, str):
            body = ""
        notes.append(f"{tag}\n{body.strip() or 'No release notes were provided.'}")
    digest = asset.get("digest")
    sha256 = None
    if isinstance(digest, str) and re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
        sha256 = digest.partition(":")[2].lower()

    return ReleaseInfo(
        current_version=current_version,
        version=latest_tag,
        notes="\n\n".join(notes),
        download_url=download_url,
        sha256=sha256,
    )


def install_update(app_dir, release):
    app_dir = Path(app_dir)
    request = urllib.request.Request(
        release.download_url, headers={"User-Agent": "PicoChestCounter"}
    )
    try:
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:
            archive_data = response.read()
    except (urllib.error.URLError, TimeoutError) as error:
        raise UpdateCheckError(
            f"Could not download update {release.version}: {error}"
        ) from error

    if release.sha256:
        actual_digest = hashlib.sha256(archive_data).hexdigest()
        if actual_digest != release.sha256:
            raise UpdateCheckError("The downloaded update failed its SHA-256 check.")

    try:
        with TemporaryDirectory(
            prefix=".pico-chest-counter-update-", dir=app_dir
        ) as temp_dir:
            archive_path = Path(temp_dir) / RELEASE_ASSET
            staged_dir = Path(temp_dir) / "staged"
            backup_dir = Path(temp_dir) / "backup"
            staged_dir.mkdir()
            backup_dir.mkdir()
            archive_path.write_bytes(archive_data)
            with zipfile.ZipFile(archive_path) as archive:
                files = {}
                for item in archive.infolist():
                    path = PurePosixPath(item.filename)
                    if (
                        item.is_dir()
                        or len(path.parts) != 1
                        or path.name not in APP_FILES
                    ):
                        continue
                    if path.name in files:
                        raise UpdateCheckError(
                            f"The update archive contains duplicate {path.name} files."
                        )
                    files[path.name] = item

                required = {
                    "pico_chest_counter.py",
                    "updater.py",
                    "app_version.txt",
                    "update-config.json",
                }
                if not required.issubset(files):
                    raise UpdateCheckError(
                        "The update archive is missing required app files."
                    )

                for name, item in files.items():
                    (staged_dir / name).write_bytes(archive.read(item))
            committed = []
            try:
                ordered_names = sorted(
                    files, key=lambda name: name == "app_version.txt"
                )
                for name in ordered_names:
                    destination = app_dir / name
                    had_original = destination.exists()
                    if had_original:
                        shutil.copy2(destination, backup_dir / name)
                    os.replace(staged_dir / name, destination)
                    committed.append((name, had_original))
            except OSError as error:
                rollback_error = None
                for name, had_original in reversed(committed):
                    try:
                        destination = app_dir / name
                        if had_original:
                            os.replace(backup_dir / name, destination)
                        else:
                            destination.unlink()
                    except OSError as rollback_failure:
                        rollback_error = rollback_failure
                if rollback_error:
                    raise UpdateCheckError(
                        f"Update failed and rollback was incomplete: {rollback_error}"
                    ) from error
                raise UpdateCheckError(
                    f"Could not install update {release.version}: {error}"
                ) from error
    except UpdateCheckError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
        raise UpdateCheckError(
            f"Could not install update {release.version}: {error}"
        ) from error
