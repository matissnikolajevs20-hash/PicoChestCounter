# Delta Chest Counter

A Windows desktop app that counts clearly recognized instances of `delta` spoken into the default microphone. Speech recognition runs locally after setup; audio is not sent to an online service. The count is saved in `chest_count.json` beside the app.

## Install and launch

1. Download and run [PicoChestCounter-Setup.exe](https://github.com/matissnikolajevs20-hash/PicoChestCounter/releases/latest). Setup installs the app and offline English speech model without requiring Python.
2. Launch **Delta Chest Counter** from the Start menu or Desktop shortcut. Right-click its shortcut and choose **Pin to taskbar** for one-click launch.
3. Select **Start listening** and allow microphone access if Windows asks.

Say `delta` naturally. The offline recognizer transcribes speech normally, and only exact, whole-word `delta` matches increase the count. Use **Reset count** to clear it and **Keep on top** to keep the app window above other windows. Select **Show mini counter** for a small, number-only overlay that stays above other windows; drag it anywhere on screen and select **Hide mini counter** when you no longer need it.

The app listens only while its **Listening** status is shown. The count is stored in your Windows local app data and survives app updates and reinstalls. Microphone access can also be managed in Windows Settings under Privacy & security > Microphone.

## Share the app and publish updates

Automatic updates use **public GitHub Releases**:

1. Share the installer from the [latest release](https://github.com/matissnikolajevs20-hash/PicoChestCounter/releases/latest). Python is not needed on users' computers.
2. For each update, change `app_version.txt` to a higher `major.minor.patch` version, commit and push the changes, then push a matching version tag, such as `v1.0.2` (`git tag v1.0.2`, then `git push origin v1.0.2`).
3. The included GitHub Actions workflow runs tests, bundles the offline model into the branded Windows app, builds `PicoChestCounter-Setup.exe`, and publishes it alongside `PicoChestCounter.zip`. The tag must match the value in `app_version.txt`; GitHub generates release notes from commits since the previous tag.

Installed apps check for updates when launched and whenever **Check for updates** is selected. If a newer release is found, the app asks whether you want to install it and shows notes for every version since the installed version. Select **Yes** to download and install the verified update, or **No** to keep using the current version. Your local count is preserved. Updates require internet access; the app still opens if the update check fails. Older source-folder installs can continue receiving the legacy source update zip; use `setup.bat` to switch them to the installed app.

## Building from source

On Windows, run `build_windows.ps1`. It creates a separate build environment, downloads the offline model, bundles the app, and compiles the installer. Python 3.12 and Inno Setup 6 are required for local builds.
