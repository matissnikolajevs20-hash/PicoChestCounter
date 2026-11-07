# Delta Chest Counter

A Windows desktop app that counts clearly recognized instances of `delta` spoken into the default microphone. Speech recognition runs locally after setup; audio is not sent to an online service. The count is saved in `chest_count.json` beside the app.

## Set up and launch

1. Install Python 3.12 or newer on Windows.
2. Double-click `setup.bat` and wait for it to finish. It installs the app's Python packages and downloads the offline English speech model.
3. Use the **Delta Chest Counter** shortcut on your Desktop or in the Start menu. Right-click either shortcut and choose **Pin to taskbar** for one-click launch.
4. Select **Start listening** and allow microphone access if Windows asks.

Say `delta` naturally. Recognition is biased toward that word, and each recognized occurrence increases the count. Use **Reset count** to clear it and **Keep on top** to keep the app window above other windows.

The app listens only while its **Listening** status is shown. Microphone access can also be managed in Windows Settings under Privacy & security > Microphone.

## Share the app and publish updates

Automatic updates use **public GitHub Releases**. GitHub is not configured until you create/share the first zip:

1. Create a public GitHub repository for the app.
2. Double-click `share.bat`, enter the repository as `owner/name`, then send the resulting `PicoChestCounter.zip` to friends. They unzip it and run `setup.bat` once; Python 3.12+ and internet access are needed for setup. Copies shared before the updater was added must be replaced with this first updated zip once.
3. Put the app files in the repository's root and push them to GitHub. Keep `update-config.json` set to that repository's `owner/name`.
4. For each update, change `app_version.txt` to a higher `major.minor.patch` version, commit and push the changes, then push a matching version tag, such as `v1.0.1` (`git tag v1.0.1`, then `git push origin v1.0.1`). The included GitHub Actions workflow builds `PicoChestCounter.zip` and publishes it as a release automatically. The tag must match the value in `app_version.txt`; the release notes are generated from commits since the previous tag.

Installed copies check for updates when launched and whenever **Check for updates** is selected. If a newer release is found, the app shows its notes for every version since the installed version. The user can choose **Install update** or **Later**. Installing downloads the release zip, checks its SHA-256 digest when GitHub provides one, installs the app files, and restarts the app. Counts are kept locally and are not overwritten. Updates require internet access; the app still opens if the update check fails. Creating a public GitHub repository and pushing a tagged version are required to host releases.
