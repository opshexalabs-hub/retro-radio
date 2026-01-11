# Retro Radio

Retro Radio is a lightweight desktop internet radio player with a nostalgic aesthetic, built using **PyQt5** and **VLC**. It supports streaming radio stations from a CSV file, displays live track metadata with debounce protection, and features a neon-style animated equalizer for visual feedback.

The application is cross-platform (macOS, Linux, Windows) provided that VLC Media Player is installed.

---

## Features

- Stream internet radio stations via VLC
- Station list loaded from a CSV file
- Debounced metadata updates (prevents flickering titles)
- Persistent settings (last station, volume)
- Volume control and mute
- Station navigation
- Neon-style animated equalizer (visual only)
- Fixed-size, minimal retro UI

---

## Requirements

### System Dependencies

- VLC Media Player  
  - macOS: `/Applications/VLC.app`  
  - Linux / Windows: `vlc` available on `PATH`

### Python Dependencies

- Python 3.8+
- PyQt5
- python-vlc

Install Python dependencies:

```bash
pip install PyQt5 python-vlc
```

---

## Project Structure

```
.
├── retro_radio.py        # Main application
├── streams.csv           # Radio station definitions
├── settings.json         # Auto-generated user settings
└── README.md
```

---

## streams.csv Format

The application loads stations from `streams.csv`.

Example:

```csv
name,url,debounce
Synthwave Radio,https://example.com/stream,3.0
Lo-Fi Beats,https://example.com/lofi,2.0
```

### Columns

- `name` (optional): Display name for the station
- `url` (required): Stream URL
- `debounce` (optional): Seconds to wait before committing metadata changes

If `debounce` is omitted or invalid, a default of 3.0 seconds is used.

---

## Running the Application

```bash
python retro_radio.py
```

On startup, the application will:

1. Verify VLC and libVLC availability
2. Load `streams.csv`
3. Restore last-used station and volume (if available)

If VLC or `python-vlc` is missing, a blocking error dialog is shown and the app exits.

---

## Controls

- ⏮ Previous station
- ▶ / ⏹ Play / Stop
- ⏭ Next station
- 🔇 / 🔊 Mute / Unmute
- Volume Slider: Adjust output volume

Metadata display:
- Last: Previously played track
- Now: Current track
- Next: Pending track (debounced)

---

## Metadata Handling

Radio metadata is polled periodically and processed with a debounce mechanism to avoid rapid title changes common in streaming radio.

Each station can define its own debounce interval via `streams.csv`.

---

## Settings Persistence

User preferences are automatically saved to:

```
settings.json
```

Stored values:
- Last played station URL
- Volume level

This file is created on exit and safely ignored if corrupted.

---

## Platform Notes

- macOS: VLC must be installed in `/Applications/VLC.app`
- Linux / Windows: VLC must be discoverable via `PATH`
- Qt slot exceptions are explicitly suppressed to avoid macOS crashes

---

## License

This project is provided as-is.  
Add a license file if you intend to distribute or open-source it.

---

## Possible Enhancements

- Favorites / presets
- Station search and filtering
- Album art support
- System tray integration
- Keyboard shortcuts
- Packaging (PyInstaller / dmg / exe)

---

## Screenshots

(Optional – add screenshots or GIFs here)

---

## Acknowledgements

- VLC Media Player
- PyQt5
