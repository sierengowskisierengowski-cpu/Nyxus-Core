#!/usr/bin/env python3
"""NYXUS · bar mascot deflisten — graffiti stick-figure on bottom bar."""
import json
import os
import subprocess
import time

HOME = os.path.expanduser("~")
ASSETS = os.path.join(HOME, ".config/eww/assets/mascot")
CONF = os.path.join(HOME, ".config/eww/nyxus.conf")

fx_on = True
if os.path.isfile(CONF):
    with open(CONF) as f:
        for line in f:
            line = line.strip()
            if line.startswith("NYXUS_BAR_FX="):
                fx_on = line.split("=", 1)[1].strip().strip('"') != "off"

IDLE_POSES = ("idle0", "idle1")
WALK_POSES = ("walk0", "walk1", "walk2", "walk3")
DANCE_POSES = ("dance0", "dance1", "dance2", "dance3")


def sprite(pose, face):
    path = os.path.join(ASSETS, f"{pose}_{face}.png")
    if not os.path.isfile(path):
        path = os.path.join(ASSETS, "idle0_happy.png")
    return {"path": path}


def run_json(cmd):
    try:
        out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL, timeout=2)
        return json.loads(out.strip().splitlines()[-1])
    except Exception:
        return None


def battery_state():
    data = run_json(os.path.join(HOME, ".config/eww/scripts/battery.sh"))
    if not data:
        return 100, "Unknown"
    return int(data.get("capacity", 100)), data.get("status", "Unknown")


def player_playing():
    data = run_json(os.path.join(HOME, ".config/eww/scripts/player.sh"))
    return data and data.get("status") == "Playing"


def notif_total():
    data = run_json(os.path.join(HOME, ".config/eww/scripts/notifications.sh"))
    return int(data.get("total", 0)) if data else 0


def emit(state):
    print(json.dumps(state), flush=True)


def main():
    emit(sprite("idle0", "happy"))
    if not fx_on:
        while True:
            time.sleep(3600)

    frame = 0
    mode = "idle"
    mode_until = 0.0
    last_notifs = notif_total()
    walk_i = 0
    dance_i = 0

    while True:
        now = time.monotonic()
        cap, status = battery_state()
        playing = player_playing()
        notifs = notif_total()

        if cap < 20 and status == "Discharging":
            mode, mode_until = "fall", now + 2.5
        elif notifs > last_notifs:
            mode, mode_until = "wave", now + 1.8
            last_notifs = notifs
        elif playing:
            mode, mode_until = "dance", now + 0.4
        elif mode == "idle" and frame % 90 == 0 and now > mode_until:
            mode, mode_until = "walk", now + 1.2

        if now >= mode_until and mode != "idle":
            mode = "idle"
            mode_until = 0.0

        if mode == "fall":
            pose, face = ("fall1" if frame % 20 > 10 else "fall0"), "angry"
        elif mode == "wave":
            pose, face = ("wave1" if frame % 12 > 6 else "wave0"), "happy"
        elif mode == "dance":
            dance_i = (dance_i + 1) % len(DANCE_POSES)
            pose, face = DANCE_POSES[dance_i], "party"
            mode_until = now + 0.35
        elif mode == "walk":
            walk_i = (walk_i + 1) % len(WALK_POSES)
            pose, face = WALK_POSES[walk_i], "cool"
        else:
            pose = IDLE_POSES[(frame // 45) % len(IDLE_POSES)]
            face = "sleepy" if cap < 35 else "happy"

        emit(sprite(pose, face))
        frame += 1
        time.sleep(1.0 / 10.0)


if __name__ == "__main__":
    main()
