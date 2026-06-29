# LMWT - Local Media Watching Tool

A PyQt6-based media browser and player for local movie and TV show collections.

## Features

- 🎬 Browse Movies and TV Shows with poster tiles
- ▶️ Video playback powered by VLC
- 📺 Season/Episode navigation for TV shows
- 📝 Continue watching tracking (SQLite)
- 🎵 Audio track selection
- 💬 Subtitle track selection
- 🔍 Search and filter media
- 🖼️ Automatic poster fetching from TMDB
- ⌨️ Keyboard shortcuts

## Requirements

- **Windows** 10/11 (Linux support planned)
- **[VLC Media Player](https://www.videolan.org/vlc/)** (64-bit) - Required
- **Python 3.10+** (if running from source)

## Quick Start (Recommended)

1. Install [VLC Media Player](https://www.videolan.org/vlc/) (64-bit)
2. Download `LMWT.exe` from [Releases](https://github.com/YOUR_USERNAME/LMWT/releases)
3. Double-click to run

## Expected Folder Structure
Movies/
  ├── Action/
  │   └── The Matrix.mp4
  └── Comedy/
      └── Superbad.mp4

TV Shows/
  ├── Drama/
  │   └── Breaking Bad/
  │       ├── poster.jpg
  │       ├── Season 1/
  │       │   └── Episode 1.mp4
  │       └── Season 2/
  └── Comedy/
      └── The Office/

## Run from Source

```bash
# Clone the repository
git clone https://github.com/98th-Hansel/LMWT.git
cd LMWT

# Install dependencies
pip install -r requirements.txt

# Run
python LMWT_app.py
