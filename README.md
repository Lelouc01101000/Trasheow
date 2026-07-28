# Trasheow

Waste classifier. uses google vision API image library (optional) and gemini flash to classify what type of waste youre holding at camera. system was tasted and made on MacOS, it should work on any operating system however instructions for making executable is only for MacOS.

## Needs
### Gemini API key
To get API key for gemini go to 
```
google AI studio website -> Dashboard -> API Keys -> Create API key -> Create key -> copy API Key
```

if you hit rate limit with your key you can just make new one, key should be pasted inside configuration menu once you open the app.

### Image Recognition API (Optional)
To have access to additional layer of classification, from image recognition libraries, however this will cost money and is completely optional:
```
Google Cloud website->IAM->Grant access->Role->Vertex AI Custom Code Service Agent role->Save->Close->Service Accounts->create service account->Permission Role->Vertex AI Custom Code Service Agent role->Click on service account email->Keys->Add key->Create new key->Json->Create
```
This will give Json file, path to which is what you will enter inside the app.

Now enable Cloud vision API:

```
APIs and services -> Enable APIs and services -> Enable APIs and services -> Cloud Vision API -> Enable
```

## Project layout

```
trasheow/
  main.py                    entry point
  requirements.txt
  Trasheow-macos.spec        PyInstaller build spec for macOS (sets Info.plist)
  core/
    config_manager.py        persistent config (credentials + settings)
    camera_handler.py        OpenCV camera capture / preview / enumeration
    vision_ai.py             Vision + Gemini classification
    sound_manager.py         capture.mp3 playback (pygame mixer)
    paths.py                 asset path resolution
  gui/
    app.py                   main window
    credentials_dialog.py    API key / credentials json entry window
    settings_dialog.py       sound / categories / camera selection window
    purple_theme.json        customtkinter color theme
  assets/
    trasheow_logo.png        
    capture.mp3            
```

## Assets

App can handle situation when this two files are missing

- `assets/trasheow_logo.png` — used as the window icon.
- `assets/capture.mp3` — played on capture if sound is enabled in Settings.

## Setup (all platforms)

```
cd trasheow
python3 -m venv venv

source venv/bin/activate        # venv\Scripts\activate -> use this instead on windows

pip install -r requirements.txt
python3 main.py
```

## Credentials
Open the app, click **Credentials** (top right, separate from Settings),
and enter:

- **Gemini API key** — from Google AI Studio. (Mandatory)
- **Google Cloud credentials JSON path** — from a service account with the
  Vertex AI / Cloud Vision role, downloaded as a key file.
 (Optional if its disabled in settings)

Both fields are masked like a password field with a Show/Hide toggle, and
are saved to a local config file so they persist across restarts:

- Windows: `%APPDATA%\Trasheow\config.json`
- macOS: `~/Library/Application Support/Trasheow/config.json`
- Linux: `~/.config/Trasheow/config.json`

If credentials are not set, the app still opens and the camera preview
still works, you'll see a banner reminding you to configure them, and clicking **Detect Waste** will show a dialog instead of crashing.

Note: the API key is stored in plain text json on disk (no OS keychain integration).

## Settings

The **Settings** window (separate from Credentials) lets you:

- toggle the capture sound on/off
- edit the list of trash categories sent to Gemini (comma separated)
- pick which camera to use, from a dropdown of cameras OpenCV actually detected on your machine.
- Google Cloud Vision API usage toggled on and off

## Building a standalone executable (PyInstaller)

Run these from inside the activated venv, from the `trasheow/` directory.

**Important — clean environment first:** if your terminal prompt shows both `(venv)` and `(base)` at the same time (a venv layered on top of an active conda environment), PyInstaller scans the combined environment and can find unrelated packages like PyQt5/PySide6 that some other tool installed into your conda base — even though Trasheow itself never uses Qt (customtkinter is built on plain tkinter). That causes a `multiple Qt bindings packages` build error. run `conda deactivate` before activating the venv, so only the venv is active, and pass the `--exclude-module` flags below as a second safety net regardless.


### macOS

macOS requires a custom `Info.plist` entry (`NSCameraUsageDescription`) before any app is allowed to touch the camera, without it the built `.app` crashes immediately on launch with a TCC privacy violation the moment it opens the camera, even though `python main.py` from source works fine (the system Python already carries that description; a frozen `.app` does not unless you add it yourself). A plain `pyinstaller --windowed ...` one-liner has no way to set this, so macOS builds use the included spec file:

```
pyinstaller Trasheow-macos.spec
```

Notes specific to macOS:

- This produces `dist/Trasheow.app`, a real double-clickable macOS app bundle. Move it to `/Applications` like any other app.
- macOS Gatekeeper will block an unsigned app the first time with an "unidentified developer" warning. Without a paid Apple Developer certificate you can't get rid of this warning entirely, but you can open it anyway with either:
  - Right-click (or Control-click) the app → **Open** → **Open** in the confirmation dialog, or
  - `xattr -cr /Applications/Trasheow.app` in Terminal, which strips the quarantine flag Gatekeeper checks.
- The first time the built app opens the camera, macOS will show a permission prompt using the description text from the spec file. It must be granted in **System Settings → Privacy & Security → Camera** or the preview will stay black. If you denied it once, re-enable it there manually — the app can't re-trigger the prompt on its own. after giving permission for the first time you have to reopen the app.
- If you change `main.py`/`gui/`/`core/` and rebuild, delete `build/` and `dist/` first (`rm -rf build dist`) so PyInstaller doesn't reuse a stale cache from a previous run.
