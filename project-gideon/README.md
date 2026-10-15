# G.I.D.E.O.N.

Voice + hand-gesture control for Hyprland on Arch Linux. Built by Nathanael George Nitin
(TEJ4M1 Computer Engineering Tech culminating project).

Two parts:

| File | What it does |
|---|---|
| `gideon_core.py` | Voice assistant + HUD. Wake word, custom voice lines, window/workspace commands |
| `gideon_vanguard.py` | Webcam hand tracking (MediaPipe): cursor, click, window drag, workspace switching |

Saying **"open your eyes"** to the core launches Vanguard.

## Requirements
- Arch Linux + Hyprland (Wayland)
- `ydotool` running with its socket at `/tmp/.ydotool_socket`, `rofi-wayland`, `kitty`
- Python 3.10+, a webcam and a microphone
- MediaPipe model: download `hand_landmarker.task` from the MediaPipe docs and put it at `~/hand_landmarker.task`

```bash
pip install -r requirements.txt
python gideon_core.py        # voice + HUD
python gideon_vanguard.py    # hand tracking on its own
```
Optional: `GIDEON_BRAIN_SCRIPT` (path for "use your brain"), `GIDEON_MODEL` (model path).

## Voice commands
Say "Gideon", wait for "Yes, Sir?", then the command.

| Say | Result |
|---|---|
| "Wake up daddy's home" | Greeting (no wake word needed) |
| "Pagliari" (+ misheard variants) | Legend line, purple HUD |
| "Nathan" | Red HUD line |
| "Double double" | Coffee order line |
| "Open your eyes" | Launches hand tracking |
| "Use your brain" | Runs your Gemini query script, green HUD |
| "Gather all windows" / "Nevermind" | Pull every window here / undo |
| "Sector 3" / "Send to sector 3" | Switch workspace / move window |
| "Go to sleep" | Quit |

All lines live in the `LINES` dict at the top of `gideon_core.py`.

## Hand controls
Modes: `NORMAL` (cyan HUD), `W_MODE` (yellow), `SPECTATOR` (red, all input off).

| Hand | Gesture | Mode | Result |
|---|---|---|---|
| Right | Index finger | any | Move cursor |
| Right | Index + thumb pinch | NORMAL | Left click |
| Right | Index + thumb pinch, move | W_MODE | Drag active window |
| Left | Ring + thumb pinch, index at far left/right | W_MODE | Previous / next workspace |
| Left | Index + middle tap | NORMAL | Fullscreen app launcher (rofi) |
| Both | Thumb tips together | any | Toggle W_MODE |
| Both | Index + pinky together on both hands | any | Toggle SPECTATOR |

## Docs
- [Troubleshooting & dev log](docs/TROUBLESHOOTING.md): every error hit while building this and how it was fixed

## Security
Never commit API keys. This repo uses none; the old Google key from the early chat versions must be revoked.
