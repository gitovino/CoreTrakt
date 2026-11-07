# CoreTrakt 🎬

> A modern, zero-configuration VLC media scrobbler for Trakt.tv with native Windows 11 UI and smart title resolution.

CoreTrakt lives quietly in your Windows system tray, communicates with VLC Media Player over its local HTTP interface, extracts clean titles via `guessit`, matches metadata with the official Trakt Search API, and scrobbles your playback progress automatically.

---

## ✨ Features

- **Smart Metadata & Fuzzy Matching**: Uses Trakt's search engine to resolve exact show IDs and titles, automatically handling missing apostrophes, alternate names, and foreign media releases.
- **Zero-Setup VLC Configuration**: Automatically configures VLC's `vlcrc` file on first launch (enables HTTP web interface and configures credentials).
- **One-Click Trakt OAuth**: Employs the official Trakt Device Code flow — no need to create developer keys or enter client secrets.
- **Modern Windows 11 Interface**: Clean, responsive dark-mode GUI built with `CustomTkinter`.
- **11 Interface Languages**: Real-time interface translation across English, Dutch, Spanish, French, German, Portuguese, Russian, Chinese, Japanese, Hindi, and Arabic.
- **Quick Launch Shortcuts**: Quick buttons inside the settings panel to launch VLC directly or view your Trakt dashboard.
- **Directory Filtering**: Limit scrobbling to selected storage folders, or monitor all media played in VLC.
- **Lightweight System Tray Resident**: Minimal RAM and CPU consumption.

---

## 🚀 Download & Installation (Standalone Executable)

You do **not** need Python installed on your computer to run CoreTrakt.

1. Download the latest **`CoreTrakt.exe`** from the [Releases](https://github.com/gitovino/CoreTrakt/releases) section.
2. Place `CoreTrakt.exe` in a directory of your choice.
3. Launch the app and click **Connect with Trakt**.
4. Enter the 8-character verification code displayed in your browser.
5. Play media in VLC — CoreTrakt will take care of the rest.

---

## 🛠️ Building from Source

### Prerequisites
- Python 3.9+
- VLC Media Player installed

### Setup & Run
```bash
git clone [https://github.com/gitovino/CoreTrakt.git](https://github.com/gitovino/CoreTrakt.git)
cd CoreTrakt

python -m pip install -r requirements.txt
python vlc_trakt_tray.py
