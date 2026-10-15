"""G.I.D.E.O.N. Core - voice assistant + HUD.

Voice lines are the Mark XXX versions, kept exactly as written (see LINES).
Saying "open your eyes" launches the hand-tracking module (gideon_vanguard.py).
"""
import os
import sys
import json
import difflib
import threading
import subprocess
from pathlib import Path

import cv2
import numpy as np
import pyttsx3
import speech_recognition as sr

os.environ.setdefault("QT_QPA_PLATFORM", "xcb")  # OpenCV windows on Wayland

HERE = Path(__file__).resolve().parent
VANGUARD = HERE / "gideon_vanguard.py"
BRAIN_SCRIPT = os.path.expanduser(os.environ.get("GIDEON_BRAIN_SCRIPT", "~/scripts/gemini-query.sh"))

# --- YOUR VOICE LINES (edit here, nothing else needs to change) ---
LINES = {
    "boot": "Gideon Online. Sharklinx Protocol active.",
    "yes": "Yes, Sir?",
    "wake": "Welcome home, Sir. I've missed our sessions. What are we doing today?",
    "eyes": "Ahh Finally, Lets have some fun shall we? Opening Visual AI.",
    "brain": "Brain Module Located, Consulting To the Cloud.",
    "brain_missing": "Sir, the Gemini script is missing from the scripts directory.",
    "double": "A Double Double, Sir? The Master's choice. I'll have the logistics ready for your arrival at Tims.",
    "undo": "Nevermind. Returning all modules to their original sectors.",
    "undo_empty": "No previous state recorded to revert to, Sir.",
    "gather": "Consolidating modules to current sector. Snapshot saved.",
    "gather_fail": "Neural snapshot failed.",
    "send": "Sending active window to sector {n}.",
    "shift": "Shifting perspective to sector {n}.",
    "nathan": "Sir, do you really think I am such a fool as to not recognize my own Master? Get out of my sight.",
    "pagliari": "Master Pagliari! The legend himself. I have purged all inferior protocols. The entire neural grid is trembling in your presence. Please let me know if you would like me to order coffee from Tims.",
    "sleep": "Understood, Sir. Deactivating, Entering Hibernation State.",
}
PAGLIARI_VARIANTS = ["pagliari", "paglieri", "palieri", "paliari", "pagliary", "polyari", "paglari"]

# --- VOICE ENGINE ---
def init_engine():
    engine = pyttsx3.init()
    engine.setProperty("rate", 185)
    for voice in engine.getProperty("voices"):
        if "female" in voice.name.lower() or "f3" in voice.id.lower():
            engine.setProperty("voice", voice.id)
            break
    return engine

engine = init_engine()
speak_lock = threading.Lock()
display_text = "NEURAL LINK ACTIVE"
glow_strength = 0
hud_color = (0, 0, 200)  # default red (BGR)
window_history = {}


def speak(text):
    global display_text, glow_strength
    with speak_lock:
        display_text, glow_strength = text, 50
        print(f"\n[G.I.D.E.O.N]: {text}")
        engine.say(text)
        engine.runAndWait()
        display_text, glow_strength = "NEURAL LINK ACTIVE", 0


def hears_pagliari(query):
    if any(v in query for v in PAGLIARI_VARIANTS):
        return True
    # fuzzy fallback: catches mishearings that aren't in the list
    return any(difflib.get_close_matches("pagliari", query.split(), n=1, cutoff=0.7))


def hypr(cmd):
    return subprocess.run(["hyprctl", "dispatch", *cmd.split(" ", 1)], stdout=subprocess.DEVNULL)


def execute_local_command(query):
    global hud_color, window_history
    query = query.lower().strip()

    if hears_pagliari(query):
        hud_color = (130, 0, 75)  # purple
        speak(LINES["pagliari"])
        return True

    if "nathan" in query:
        hud_color = (0, 0, 200)
        speak(LINES["nathan"])
        return True

    if "open your eyes" in query or "open eyes" in query:
        speak(LINES["eyes"])
        subprocess.Popen(["hyprctl", "dispatch", "exec", f"kitty {sys.executable} {VANGUARD}"])
        return True

    if "use your brain" in query:
        if os.path.exists(BRAIN_SCRIPT):
            hud_color = (0, 255, 0)  # green
            speak(LINES["brain"])
            subprocess.Popen(["hyprctl", "dispatch", "exec", BRAIN_SCRIPT])
        else:
            speak(LINES["brain_missing"])
        return True

    if "double double" in query:
        speak(LINES["double"])
        return True

    if "nevermind" in query or "never mind" in query:
        if not window_history:
            speak(LINES["undo_empty"])
        else:
            speak(LINES["undo"])
            for addr, ws in window_history.items():
                hypr(f"movetoworkspacesilent {ws},address:{addr}")
            window_history = {}
        return True

    if "gather all windows" in query or "bring everything here" in query:
        speak(LINES["gather"])
        try:
            clients = json.loads(subprocess.check_output(["hyprctl", "clients", "-j"]))
            window_history = {c["address"]: c["workspace"]["id"] for c in clients}
            mons = json.loads(subprocess.check_output(["hyprctl", "monitors", "-j"]))
            here = mons[0]["activeWorkspace"]["id"]
            for addr in window_history:
                hypr(f"movetoworkspace {here},address:{addr}")
        except Exception as e:
            print("gather failed:", e)
            speak(LINES["gather_fail"])
        return True

    if "sector" in query:
        num = "".join(ch for ch in query if ch.isdigit())
        if num:
            if "send" in query or "throw" in query:
                speak(LINES["send"].format(n=num))
                hypr(f"movetoworkspace {num}")
            else:
                speak(LINES["shift"].format(n=num))
                hypr(f"workspace {num}")
            return True

    if "go sleep" in query or "go to sleep" in query:
        speak(LINES["sleep"])
        os._exit(0)

    return False


def neural_listener():
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.5)
        while True:
            try:
                audio = r.listen(source, timeout=None, phrase_time_limit=4)
                heard = r.recognize_google(audio).lower()
                if "wake up daddy's home" in heard or "wake up daddys home" in heard:
                    speak(LINES["wake"])
                elif "gideon" in heard:
                    speak(LINES["yes"])
                    cmd = r.recognize_google(r.listen(source, timeout=5))
                    print("heard command:", cmd)
                    execute_local_command(cmd)
            except (sr.UnknownValueError, sr.WaitTimeoutError):
                pass  # normal: silence / unintelligible
            except Exception as e:
                print("listener error:", repr(e))  # no more silent failures


def main():
    threading.Thread(target=neural_listener, daemon=True).start()
    threading.Thread(target=speak, args=(LINES["boot"],), daemon=True).start()
    while True:
        hud = np.zeros((500, 640, 3), dtype=np.uint8)
        g = glow_strength
        cv2.circle(hud, (320, 200), 85 + g // 4, hud_color, 2)
        cv2.circle(hud, (320, 200), 10 + g // 2, (0, 215, 255), -1)
        cv2.putText(hud, "SHARKLINX PROTOCOL: SECURE", (20, 40), 1, 1, (0, 215, 255), 1)
        text = display_text
        for i, line in enumerate([text[i:i + 45] for i in range(0, len(text), 45)][:3]):
            cv2.putText(hud, line, (40, 420 + i * 25), 1, 1, (255, 255, 255), 1)
        cv2.imshow("G.I.D.E.O.N. CORE", hud)
        if cv2.waitKey(10) & 0xFF == ord("q"):
            os._exit(0)


if __name__ == "__main__":
    main()
