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
VOICE = "fr-FR-DeniseNeural"
RATE = "-6%"
LOGO = r"E:\Africa CDC\DHIS\EBOLA\Logistics\openboxes\aeris\branding\africacdc_logo_full.png"
WORK = os.path.join(HERE, "build")
os.makedirs(WORK, exist_ok=True)

CHAPTERS = {
    1: ("Se connecter", ["Ouvrir AERIS", "Mettre l'écran en français", "Choisir son entrepôt"]),
    2: ("Le tableau de bord", ["Les indicateurs", "Les menus utiles", "La recherche"]),
    3: ("Recevoir une livraison", ["Enregistrer l'entrée", "Une ligne par lot", "Réceptionner ce qui est compté"]),
    4: ("Consulter le stock", ["Rechercher un article", "Voir les lots et les expirations"]),
    5: ("Distribuer : la sortie", ["Créer la sortie", "AERIS choisit les lots", "Imprimer le bon de sortie"]),
    6: ("Transférer vers Isiro ou Beni", ["Une sortie vers un entrepôt", "La réception à l'arrivée"]),
    7: ("Le comptage physique", ["Télécharger le stock", "Compter et noter les écarts", "Charger le fichier"]),
    8: ("La fiche de stock Excel", ["Choisir l'article et la période", "Télécharger", "Contrôler le solde"]),
}
INTRO = ("Bienvenue dans cette formation sur AERIS, le système de gestion des stocks de la riposte Ebola "
         "d'Africa CDC. En quelques minutes, vous allez voir comment vous connecter, recevoir une livraison, "
         "distribuer avec un bon de sortie, transférer vers un autre entrepôt, faire un comptage, et sortir "
         "une fiche de stock en Excel.")
CHAPTER_SAY = {
    1: "Première étape : se connecter.",
    2: "Découvrons le tableau de bord.",
    3: "Recevoir une livraison. C'est l'opération la plus importante : tout ce qui entre doit être enregistré "
       "lot par lot.",
    4: "Consulter le stock d'un article.",
    5: "Distribuer des intrants : la sortie, et son bon de sortie.",
    6: "Transférer des intrants vers un autre entrepôt d'Africa CDC.",
    7: "Le comptage physique.",
    8: "Et enfin, la fiche de stock au format Excel.",
}
RULES = [
    "Vérifiez l'entrepôt affiché avant chaque opération",
    "Enregistrez chaque mouvement le jour même",
    "Une ligne par lot, avec sa date d'expiration",
    "Dates en chiffres : jour / mois / année",
    "Faites signer et classez chaque bon de sortie",
    "Un écart ? Un commentaire, et prévenez le responsable",
]
RULES_SAY = ("Pour finir, les bons réflexes. Vérifiez toujours l'entrepôt affiché en haut à gauche. Enregistrez "
             "chaque mouvement le jour même, sans attendre. Une ligne par lot, avec sa date d'expiration. Tapez "
             "les dates en chiffres : jour, mois, année. Faites signer et classez chaque bon de sortie. Et pour "
             "tout écart, mettez un commentaire et prévenez votre responsable logistique. "
             "En cas de question, contactez le point focal Aéris de votre équipe. Merci, et bon travail !")


def for_voice(text):
    t = text.replace("AERIS", "Aéris").replace("BCZ", "B C Z").replace("MCM", "M C M")
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
    steps = json.load(open(os.path.join(HERE, "steps.json"), encoding="utf-8"))
    segs = []
    n = 0

    def add(image, say):
        nonlocal n
        n += 1
        segs.append(segment(n, image, say))
        print(f"  segment {n}: {segs[-1][1]:.1f}s")

    title = os.path.join(WORK, "title.jpg")
    F.title_card("AERIS – Formation des magasiniers",
                 "Recevoir, distribuer, transférer, compter et exporter le stock de la riposte Ebola",
                 title, LOGO, "Africa CDC · Riposte Ebola · Entrepôts de Bunia, Isiro et Beni")
    add(title, INTRO)
    for ch in sorted(CHAPTERS, key=int):
        name, points = CHAPTERS[ch]
        card = os.path.join(WORK, f"chapter{ch}.jpg")
        F.chapter_card(ch, name, points, card)
        add(card, CHAPTER_SAY[ch])
        for st in steps.get(str(ch), []):
            img = os.path.join(WORK, "f_" + os.path.splitext(st["img"])[0] + ".jpg")
            F.compose(os.path.join(HERE, "shots", st["img"]), st["caption"], f"{ch} · {name}",
                      st["boxes"], img)
            add(img, st["say"])
    rules = os.path.join(WORK, "rules.jpg")
    F.chapter_card(9, "Les bons réflexes", RULES, rules)
    add(rules, RULES_SAY)
    end = os.path.join(WORK, "end.jpg")
    F.title_card("Merci !", "Questions : le point focal AERIS de votre équipe", end, LOGO,
                 "Africa CDC · AERIS")
    add(end, "Fin de la formation.")

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
