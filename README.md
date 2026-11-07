# CoreTrakt

CoreTrakt is a Windows system tray utility that scrobbles media played in VLC Media Player to Trakt.tv. It queries VLC's local web interface, extracts media titles and episode numbers from filenames, resolves metadata against Trakt's API, and updates playback progress in real time.

---

## Features

- **Automated VLC Configuration:** Automatically configures VLC's web interface and credentials in `vlcrc` on launch.
- **Title and Metadata Resolution:** Uses `guessit` alongside Trakt's search API to resolve show titles, movie releases, missing punctuation, and alternate language titles.
- **Trakt Device Code Authentication:** Connects to Trakt via the official OAuth device authentication flow without requiring custom developer credentials.
- **Directory Filtering:** Optionally restrict scrobbling to specific folders, or track all playback across the system.
- **System Tray Operation:** Runs in the Windows system tray with minimal memory and CPU usage.
- **Single-Instance Enforcement:** Uses a Windows mutex to prevent duplicate running instances, localized to the active system language.
- **Windows Startup Integration:** Built-in option to launch automatically with Windows.
- **Multi-Language UI:** Settings interface localized in English, Dutch, Spanish, French, German, Portuguese, Russian, Chinese, Japanese, Hindi, and Arabic.

---

## Installation

Precompiled standalone binaries for Windows 10 and 11 are available on the releases page. Python is not required to run the standalone executable.

1. Download `CoreTrakt.exe` from the [Releases](https://github.com/gitovino/CoreTrakt/releases) section.
2. Place the executable in a preferred directory.
3. Launch `CoreTrakt.exe`.
4. Click **Connect with Trakt** and complete the authorization prompt in your browser.
5. Start VLC. Media will scrobble automatically during playback.

---

## Running from Source

### Requirements

- Windows 10 or 11
- Python 3.9+
- VLC Media Player

### Installation

Clone the repository and install the required dependencies:

```bash
git clone [https://github.com/gitovino/CoreTrakt.git](https://github.com/gitovino/CoreTrakt.git)
cd CoreTrakt

python -m pip install -r requirements.txt
python vlc_trakt_tray.py
