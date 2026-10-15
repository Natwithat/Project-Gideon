# Troubleshooting & Dev Log

Every problem hit while building G.I.D.E.O.N., what caused it, and the fix.

| # | Problem | Cause | Fix |
|---|---|---|---|
| 1 | Mouse control tools did nothing on Hyprland | Wayland blocks apps from moving the cursor (xdotool is X11-only) | Use `ydotool` (virtual device via uinput, needs its socket: `YDOTOOL_SOCKET=/tmp/.ydotool_socket`) and `hyprctl dispatch movecursor` |
| 2 | OpenCV window crashed / wouldn't open on Wayland | Qt Wayland plugin issue | `QT_QPA_PLATFORM=xcb` at the top of the script |
| 3 | "Open your eyes" opened nano/nvim instead of `gideon.py` | Chained `sh -c` wrappers and path building mangled the command | Launch the interpreter and script directly: `kitty python <script>` |
| 4 | Voice never reacted to "Pagliari" | Google speech-to-text mishears the name | Variant list + `difflib` fuzzy match fallback + `dynamic_energy_threshold` |
| 5 | Skeleton overlay looked messy | Wrong landmark chains | Chains per finger + knuckle line (5,9,13,17) + palm base (0,17) |
| 6 | Window drag didn't work | `movewindow pixel/m` is meant for mouse binds; `moveactive` only moves **floating** windows | Move by per-frame delta with `moveactive`, and `setfloating` first if the window is tiled |
| 7 | Cursor and window stuttered | Raw landmarks jitter, `hyprctl` spawned every frame, `time.sleep()` froze the loop | Exponential smoothing (alpha 0.35), only call `hyprctl` when the position changed by >1px, cooldown timestamps instead of sleeps |
| 8 | Click stopped working | Button-down (`0x40`) / button-up (`0x80`) got out of sync and the button stuck | Single pulse click `0xC0` guarded by a `pinching` flag, plus a release (`0x80`) on startup |
| 9 | App launcher small / froze everything | `-fullscreen` alone didn't take, and `subprocess.run` blocks until rofi closes | `Popen` + `-theme-str 'window {fullscreen: true;}'`, don't relaunch while running |
| 10 | Workspace switching spammed | No debounce | 0.7s cooldown per action |
| 11 | Hardcoded 3840x1080 screen size | Only valid for one monitor setup | Read monitors from `hyprctl monitors -j` |
| 12 | Voice lines got changed by the AI between versions | Whole files were regenerated each time | Lines moved into one `LINES` dict, commit to git so changes are visible in diffs |
| 13 | Later "master" builds lost features | Mark XXXII/XXXIII dropped W_MODE, SPECTATOR, sector commands, drag, and clicked every frame while pinched | Rebuilt from the Input Recovery (vision) + Mark XXX (voice) builds |
| 14 | Errors were invisible | `except: pass` everywhere | Only ignore expected speech errors, print the rest |
| 15 | Google API key sitting in source | Pasted into early versions | Removed (the key was never used). Revoke it in Google Cloud Console |

## Version history
- Vanguard: first build -> sticky drag -> smoothing -> input recovery (best)
- Core: Mark XXIV-XXVII (eyes/path fixes) -> XXVIII hybrid -> XXX coffee & commands (best voice)
- Mark XXXII/XXXIII: merged attempts that regressed (not used)
- Repo version: Core (XXX) + Vanguard (Input Recovery) split into two files with the fixes above

## Ideas
- Local speech recognition (e.g. Vosk) so it works offline
- Pinch-to-resize windows
- Config file for thresholds and voice lines
