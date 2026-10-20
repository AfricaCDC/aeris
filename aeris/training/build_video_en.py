"""Assemble the AERIS storekeeper training video: title, chapters, captured steps, French narration.

python build_video.py <out.mp4>
Needs steps.json + shots/ (capture.py, excel_shots.py), edge-tts (network) and imageio-ffmpeg.
"""
import asyncio
import json
import os
import re
import subprocess
import sys
import wave

import edge_tts
import imageio_ffmpeg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frames as F  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VOICE = "en-GB-SoniaNeural"
RATE = "-4%"
LOGO = r"E:\Africa CDC\DHIS\EBOLA\Logistics\openboxes\aeris\branding\africacdc_logo_full.png"
WORK = os.path.join(HERE, "build_en")
os.makedirs(WORK, exist_ok=True)

CHAPTERS = {
    1: ("Signing in", ["Open AERIS", "Choose the language", "Choose your warehouse"]),
    2: ("The dashboard", ["The indicators", "The useful menus", "Search"]),
    3: ("Receiving a delivery", ["Record the inbound movement", "One line per batch", "Receive what you counted"]),
    4: ("Looking up stock", ["Search for an item", "See batches and expiry dates"]),
    5: ("Issuing stock", ["Create the issue", "AERIS picks the batches", "Print the delivery note"]),
    6: ("Transfers to Isiro or Beni", ["An issue to a warehouse", "Receiving on arrival"]),
    7: ("Physical count", ["Download the stock", "Count and note differences", "Upload the file"]),
    8: ("The Excel stock card", ["Choose item and period", "Download", "Check the balance"]),
}
INTRO = ("Welcome to this training on AERIS, the stock management system of the Africa CDC Ebola response. "
         "In a few minutes you will see how to sign in, receive a delivery, issue stock with a delivery note, "
         "transfer to another warehouse, do a physical count, and export a stock card to Excel.")
CHAPTER_SAY = {
    1: "First step: signing in.",
    2: "Let's look at the dashboard.",
    3: "Receiving a delivery. This is the most important operation: everything that comes in must be recorded "
       "batch by batch.",
    4: "Looking up the stock of an item.",
    5: "Issuing supplies: the outbound movement and its delivery note.",
    6: "Transferring supplies to another Africa CDC warehouse.",
    7: "The physical count.",
    8: "And finally, the stock card in Excel.",
}
RULES = [
    "Check the warehouse shown before every operation",
    "Record every movement on the same day",
    "One line per batch, with its expiry date",
    "Dates as numbers: day / month / year",
    "Have every delivery note signed, and file it",
    "Any difference? Add a comment and tell your supervisor",
]
RULES_SAY = ("To finish, the good habits. Always check the warehouse shown at the top left. Record every movement "
             "on the same day, without waiting. One line per batch, with its expiry date. Type dates as numbers: "
             "day, month, year. Have every delivery note signed, and file it. And for any difference, add a "
             "comment and tell your logistics lead. If you have questions, contact the AERIS focal point in your "
             "team. Thank you, and good work!")


def for_voice(text):
    t = text.replace("AERIS", "Airis").replace("BCZ", "B C Z").replace("MCM", "M C M")
    t = re.sub(r"\bQOH\b", "", t)
    return t


async def tts(text, mp3):
    await edge_tts.Communicate(for_voice(text), VOICE, rate=RATE).save(mp3)


def run(args):
    subprocess.run([FFMPEG, "-y", "-loglevel", "error"] + args, check=True)


def audio_seconds(mp3, wav):
    run(["-i", mp3, "-ar", "44100", "-ac", "2", wav])
    with wave.open(wav) as w:
        return w.getnframes() / w.getframerate()


def segment(idx, image, say, pad_before=0.35, pad_after=0.9):
    """Image + narration -> mp4 segment. Returns (path, duration, narration)."""
    base = os.path.join(WORK, f"seg{idx:03d}")
    mp3, wav, mp4 = base + ".mp3", base + ".wav", base + ".mp4"
    if not os.path.exists(mp3):
        asyncio.run(tts(say, mp3))
    dur = audio_seconds(mp3, wav) + pad_before + pad_after
    run(["-loop", "1", "-framerate", "30", "-i", image,
         "-i", wav, "-filter_complex",
         f"[1:a]adelay={int(pad_before * 1000)}|{int(pad_before * 1000)},apad[a];"
         f"[0:v]scale=1920:1080,format=yuv420p,fade=t=in:st=0:d=0.25[v]",
         "-map", "[v]", "-map", "[a]", "-t", f"{dur:.2f}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-tune", "stillimage",
         "-c:a", "aac", "-b:a", "160k", "-ar", "44100", mp4])
    return mp4, dur, say


def srt_time(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s - int(s)) * 1000):03d}"


def main():
    steps = json.load(open(os.path.join(HERE, "steps_en.json"), encoding="utf-8"))
    segs = []
    n = 0

    def add(image, say):
        nonlocal n
        n += 1
        segs.append(segment(n, image, say))
        print(f"  segment {n}: {segs[-1][1]:.1f}s")

    title = os.path.join(WORK, "title.jpg")
    F.title_card("AERIS – Storekeeper training",
                 "Receiving, issuing, transferring, counting and exporting Ebola response stock",
                 title, LOGO, "Africa CDC · Ebola response · Bunia, Isiro and Beni warehouses")
    add(title, INTRO)
    for ch in sorted(CHAPTERS, key=int):
        name, points = CHAPTERS[ch]
        card = os.path.join(WORK, f"chapter{ch}.jpg")
        F.chapter_card(ch, name, points, card)
        add(card, CHAPTER_SAY[ch])
        for st in steps.get(str(ch), []):
            img = os.path.join(WORK, "f_" + os.path.splitext(st["img"])[0] + ".jpg")
            F.compose(os.path.join(HERE, "shots_en", st["img"]), st["caption"], f"{ch} · {name}",
                      st["boxes"], img)
            add(img, st["say"])
    rules = os.path.join(WORK, "rules.jpg")
    F.chapter_card(9, "Good habits", RULES, rules)
    add(rules, RULES_SAY)
    end = os.path.join(WORK, "end.jpg")
    F.title_card("Thank you!", "Questions: the AERIS focal point in your team", end, LOGO,
                 "Africa CDC · AERIS")
    add(end, "End of the training.")

    # concat + subtitles
    lst = os.path.join(WORK, "list.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for path, _, _ in segs:
            f.write(f"file '{path.replace(os.sep, '/')}'\n")
    run(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", OUT])
    t = 0.0
    with open(os.path.splitext(OUT)[0] + ".srt", "w", encoding="utf-8") as f:
        for i, (_, dur, say) in enumerate(segs, 1):
            f.write(f"{i}\n{srt_time(t + 0.3)} --> {srt_time(t + dur - 0.5)}\n{say}\n\n")
            t += dur
    print(f"video: {OUT}  ({t / 60:.1f} min, {len(segs)} segments)")


main()
