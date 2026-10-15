"""G.I.D.E.O.N. Vanguard - hand-gesture control for Hyprland (Wayland).

Built on the "Input Recovery" build: smoothing + pulse click + sticky drag.
Fixes over the chat versions: no blocking sleeps, rofi no longer freezes the loop,
auto screen size, tiled windows float before dragging, hyprctl only called on change.
"""
import os
import json
import math
import time
import subprocess
from pathlib import Path

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("YDOTOOL_SOCKET", "/tmp/.ydotool_socket")

# --- CONFIG ---
MODEL_PATH = os.path.expanduser(os.environ.get("GIDEON_MODEL", "~/hand_landmarker.task"))
SWAP_HANDEDNESS = True      # set False if your left/right hands are reversed
CLICK_PINCH = 0.05          # index+thumb distance that counts as a pinch
RING_PINCH = 0.05
TAP_DIST = 0.04             # index+middle tap (app launcher)
TOGGLE_PINCH = 0.06
SMOOTH_ALPHA = 0.35
FALLBACK_SCREEN = (0, 0, 3840, 1080)

CONNECTIONS = [(0, 1, 2, 3, 4), (0, 5, 6, 7, 8), (9, 10, 11, 12),
               (13, 14, 15, 16), (17, 18, 19, 20), (5, 9, 13, 17), (0, 17)]


def hypr(*args):
    subprocess.run(["hyprctl", "dispatch", *args], stdout=subprocess.DEVNULL)


def screen_bounds():
    """x, y, width, height covering all monitors (falls back to 3840x1080)."""
    try:
        mons = json.loads(subprocess.check_output(["hyprctl", "monitors", "-j"]))
        x0 = min(m["x"] for m in mons)
        y0 = min(m["y"] for m in mons)
        x1 = max(m["x"] + m["width"] for m in mons)
        y1 = max(m["y"] + m["height"] for m in mons)
        return x0, y0, x1 - x0, y1 - y0
    except Exception:
        return FALLBACK_SCREEN


def active_window_floating():
    try:
        return json.loads(subprocess.check_output(["hyprctl", "activewindow", "-j"])).get("floating", True)
    except Exception:
        return True


def dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


class HandSmooth:
    def __init__(self, alpha=SMOOTH_ALPHA):
        self.prev, self.alpha = None, alpha

    def smooth(self, cur):
        cur = np.array(cur, dtype=float)
        self.prev = cur if self.prev is None else self.alpha * cur + (1 - self.alpha) * self.prev
        return self.prev


class Cooldowns:
    def __init__(self):
        self.t = {}

    def ready(self, name, secs):
        now = time.time()
        if now - self.t.get(name, 0) >= secs:
            self.t[name] = now
            return True
        return False


def draw_hud(img, lm, color, h, w):
    for chain in CONNECTIONS:
        for a, b in zip(chain, chain[1:]):
            cv2.line(img, (int(lm[a].x * w), int(lm[a].y * h)),
                     (int(lm[b].x * w), int(lm[b].y * h)), color, 2, cv2.LINE_AA)
    for p in lm:
        c = (int(p.x * w), int(p.y * h))
        cv2.circle(img, c, 5, (255, 255, 255), -1)
        cv2.circle(img, c, 8, color, 1, cv2.LINE_AA)


def main():
    sx, sy, sw, sh = screen_bounds()
    options = vision.HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=vision.RunningMode.VIDEO, num_hands=2)

    subprocess.run(["ydotool", "click", "0x80"], stdout=subprocess.DEVNULL)  # release stuck button
    smooth, cd = HandSmooth(), Cooldowns()
    mode, pinching = "NORMAL", False
    prev, last_cursor, rofi = None, None, None
    cap = cv2.VideoCapture(0)

    with vision.HandLandmarker.create_from_options(options) as landmarker:
        print("[G.I.D.E.O.N.] Vanguard online. Press q in the window to quit.")
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            res = landmarker.detect_for_video(rgb, int(time.time() * 1000))
            color = {"NORMAL": (255, 255, 0), "SPECTATOR": (0, 0, 255)}.get(mode, (0, 255, 255))

            if res.hand_landmarks:
                if len(res.hand_landmarks) == 2 and cd.ready("toggle", 1.2):
                    h1, h2 = res.hand_landmarks
                    if dist(h1[8], h1[20]) < TOGGLE_PINCH and dist(h2[8], h2[20]) < TOGGLE_PINCH:
                        mode = "NORMAL" if mode == "SPECTATOR" else "SPECTATOR"
                    elif dist(h1[4], h2[4]) < TOGGLE_PINCH:
                        mode = "NORMAL" if mode == "W_MODE" else "W_MODE"
                    else:
                        cd.t["toggle"] = 0  # nothing fired, don't burn the cooldown

                for i, lm in enumerate(res.hand_landmarks):
                    draw_hud(frame, lm, color, h, w)
                    if mode == "SPECTATOR":
                        continue
                    label = res.handedness[i][0].category_name
                    if SWAP_HANDEDNESS:
                        label = "Left" if label == "Right" else "Right"
                    t, idx, mid, ring = lm[4], lm[8], lm[12], lm[16]

                    if label == "Right":  # cursor, click, drag
                        sc = smooth.smooth([sx + idx.x * sw, sy + idx.y * sh])
                        cx, cy = int(sc[0]), int(sc[1])
                        if last_cursor is None or abs(cx - last_cursor[0]) > 1 or abs(cy - last_cursor[1]) > 1:
                            hypr("movecursor", f"{cx} {cy}")
                            last_cursor = (cx, cy)

                        if dist(idx, t) < CLICK_PINCH:
                            if mode == "W_MODE":
                                if prev is None and not active_window_floating():
                                    hypr("setfloating")  # moveactive only moves floating windows
                                if prev is not None:
                                    dx, dy = cx - prev[0], cy - prev[1]
                                    if abs(dx) > 1 or abs(dy) > 1:
                                        hypr("moveactive", f"{dx} {dy}")
                                prev = (cx, cy)
                            elif not pinching:
                                subprocess.run(["ydotool", "click", "0xC0"], stdout=subprocess.DEVNULL)
                                pinching = True
                        else:
                            pinching, prev = False, None

                    else:  # left hand: workspaces + launcher
                        if mode == "W_MODE" and dist(ring, t) < RING_PINCH:
                            if idx.x < 0.3 and cd.ready("ws", 0.7):
                                hypr("workspace", "e-1")
                            elif idx.x > 0.7 and cd.ready("ws", 0.7):
                                hypr("workspace", "e+1")
                        elif mode == "NORMAL" and dist(idx, mid) < TAP_DIST and cd.ready("rofi", 1.2):
                            if rofi is None or rofi.poll() is not None:
                                rofi = subprocess.Popen(  # Popen: don't freeze the loop
                                    ["rofi", "-show", "drun", "-theme-str", "window {fullscreen: true;}"])

            cv2.putText(frame, f"GIDEON VANGUARD | {mode}", (25, 45), 1, 1.8, color, 3)
            cv2.imshow("GIDEON FEED", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
