# video-deconstruct

Extrait le **transcript**, des **frames** et les **statistiques publiques** (vues, likes, partages...) d'une vidéo en ligne (TikTok, YouTube, Shorts, Reels, X/Twitter, Facebook...) pour la décortiquer. Utilisable seul (script Python) ou comme skill Claude Code.

*English summary: a small Python wrapper around `yt-dlp` and `ffmpeg` that downloads a public online video and outputs its transcript (original-language subtitles, optional Whisper fallback), evenly spaced frames, public stats and a readable `summary.md`. `SKILL.md` adds a 6-axis reading grid so an LLM (Claude Code) can analyse hook, structure and pacing. Free, MIT.*

## Ce que fait l'outil

- Télécharge la vidéo avec `yt-dlp` et récupère les métadonnées publiques.
- Extrait le transcript à partir des sous-titres existants (langue d'origine).
- Si aucun sous-titre : fallback optionnel avec Whisper (transcription locale).
- Extrait N images régulièrement espacées avec `ffmpeg`.
- Écrit un `summary.md` lisible et prêt à analyser.
- Fournit dans `SKILL.md` une grille d'analyse narrative en 6 axes (accroche, structure, cadence, payoff, fin, faits).

## Ce que l'outil ne fait pas

- Il ne contourne rien : vidéos privées, géo-bloquées ou payantes = échec annoncé.
- Il n'invente jamais de transcript : sans sous-titres ni Whisper, il indique `subtitles_status: none`.
- Il n'extrait pas les commentaires.
- Il ne génère pas de script à votre place : la grille d'analyse demande une lecture humaine ou un LLM.
- Respectez les conditions d'utilisation des plateformes et le droit d'auteur : l'outil sert à analyser, pas à republier le contenu d'autrui.

## Prérequis

- Python 3.10+
- `yt-dlp` : `pip install --user yt-dlp`
- `ffmpeg` dans le PATH ([ffmpeg.org](https://ffmpeg.org/download.html))
- Optionnel : `pip install --user openai-whisper` (fallback transcription)

## Installation en 3 étapes

1. Cloner le dépôt : `git clone https://github.com/No-Dream-Ai/video-deconstruct.git video-deconstruct`
2. Installer les prérequis ci-dessus et vérifier `ffmpeg -version`.
3. (Optionnel, pour Claude Code) copier le dossier dans `~/.claude/skills/video-deconstruct/` : le skill se déclenche quand vous collez une URL de vidéo.

## Exemple

```bash
python extract.py --url "<URL_VIDEO>" --frames 8 --out "./sorties/ma-video"
```

Produit : `video.mp4`, `video.info.json`, `script.txt`, `frames/frame_<t>s.jpg`, `summary.md`. L'option `--whisper off|auto|on` règle le fallback de transcription.

## Licence

MIT, voir [LICENSE](LICENSE). Les outils tiers (yt-dlp, ffmpeg, Whisper) ont leurs propres licences et ne sont pas inclus dans ce dépôt.

## Plus d'outils No Dream

Cet outil est offert par la boutique No Dream : https://nodream-apercu-v73kq.netlify.app/prototype-5/
