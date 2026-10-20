# AERIS training videos (storekeepers, French and English)

Regenerates `AERIS_formation_magasiniers.mp4` (about 10 minutes, 1080p, French narration and captions) from a
running local AERIS. Scenes: sign in, dashboard, receiving a donation, stock lookup, issue with bon de sortie,
transfer to Isiro, stock count upload, MCM stock card export, good habits.

Needs: Windows with Chrome and Excel, Python with `playwright imageio-ffmpeg edge-tts openpyxl pywin32 pillow`.
The narration uses Microsoft's online neural voice (edge-tts, fr-FR-DeniseNeural): the narration text is sent to
that service. The demo storekeeper login comes from `aeris/tools/test-accounts.local.txt` (git-excluded).

    python excel_shots.py count                      # count file shown in scene 7
    python capture.py <path to openboxes> 1 2 3 4 5 6 7 8
    python excel_shots.py card fiche_ringer.xlsx     # stock card picture for scene 8
    python build_video.py <out.mp4>

Each capture run creates real movements in the database it points at: use a test copy, never production.

English version (`AERIS_training_storekeepers_EN.mp4`, English interface, voice en-GB-SoniaNeural):

    python excel_shots.py count en
    python capture_en.py <path to openboxes> 1 2 3 4 5 6 7 8
    python excel_shots.py card fiche_ringer_en.xlsx en
    python build_video_en.py <out.mp4>
