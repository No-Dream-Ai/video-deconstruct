#!/usr/bin/env python3
"""
video-deconstruct/extract.py — récupère transcript + N frames + stats virales
d'une vidéo en ligne (TikTok / YouTube / Reels / etc.) via yt-dlp + ffmpeg.

Usage :
    PYTHONIOENCODING=utf-8 python extract.py --url <URL> --frames 8 --out <DIR>

Outputs dans <DIR> :
    - video.mp4              vidéo téléchargée (full quality dispo)
    - video.info.json        metadata complète yt-dlp
    - video.description      description du post (souvent juste les hashtags)
    - script.txt             transcript verbatim (FR > EN > rien)
    - subs.<lang>.vtt        sous-titres bruts (si dispo)
    - frames/frame_<t>s.jpg  N frames espacées régulièrement
    - summary.md             résumé lisible (stats virales + script + frames)

Le script écrit aussi un JSON court sur stdout pour qu'un orchestrateur
sache où regarder ensuite :
    {"out_dir": "...", "summary": "...", "script": "...", "frames": [...]}

Fallback Whisper — si aucun sous-titre n'est dispo (ni manuel ni auto) et que
`whisper` (openai-whisper) est installé, le script transcrit la vidéo en FR
(`--whisper auto`, défaut). `--whisper off` désactive, `--whisper on` force la
transcription même si des subs existent (utile si les subs auto sont mauvais).
Le `.srt` produit est gardé dans <DIR> et `subtitles_source` vaut `whisper`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

# Langues à essayer pour subtitles, par ordre de préférence.
LANG_PREFERENCE = ["fra-FR", "fr-FR", "fr", "eng-US", "en-US", "en"]


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    """Wrapper subprocess.run qui n'éclate pas sur les codes de retour non-zero."""
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


def yt_dlp_download(url: str, out_dir: Path) -> dict:
    """Télécharge la vidéo + metadata + subtitles. Retourne le dict info parsé."""
    out_tpl = str(out_dir / "video.%(ext)s")
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-f", "best[ext=mp4]/best",
        "--write-info-json",
        "--write-description",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", "fr.*,en.*,fra.*,eng.*",
        "--sub-format", "vtt",
        "--no-write-thumbnail",
        "-o", out_tpl,
        url,
    ]
    print(f"[yt-dlp] downloading {url}", file=sys.stderr)
    res = run(cmd)
    # yt-dlp écrit sur stderr ; on relaie quand même pour debug.
    if res.returncode != 0:
        print("[yt-dlp STDERR]\n" + res.stderr, file=sys.stderr)
        raise SystemExit(f"yt-dlp failed (exit {res.returncode})")
    info_path = out_dir / "video.info.json"
    if not info_path.exists():
        raise SystemExit(f"info.json not found at {info_path}")
    with info_path.open(encoding="utf-8") as f:
        return json.load(f)


def pick_subtitle_url(info: dict) -> tuple[str | None, str | None, str | None]:
    """
    Retourne (lang, source, url) du meilleur track de subs disponible.
    source = 'manual' ou 'auto'. (None, None, None) si rien.
    """
    manual = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}
    for lang in LANG_PREFERENCE:
        if lang in manual and manual[lang]:
            return lang, "manual", manual[lang][0].get("url")
        if lang in auto and auto[lang]:
            return lang, "auto", auto[lang][0].get("url")
    # Fallback : prendre n'importe quelle langue dispo.
    for src_name, src in (("manual", manual), ("auto", auto)):
        for lang, tracks in src.items():
            if tracks:
                return lang, src_name, tracks[0].get("url")
    return None, None, None


def download_subs(url: str, dest: Path) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read().decode("utf-8", "replace")
        dest.write_text(data, encoding="utf-8")
        return True
    except Exception as e:
        print(f"[subs] download failed: {e}", file=sys.stderr)
        return False


def vtt_to_plain(vtt_text: str) -> str:
    """
    Convertit un WEBVTT en plain text :
    - vire l'en-tête WEBVTT
    - vire les lignes de timestamps (--> ou tags de positionnement)
    - vire les balises <c>…</c> et autres
    - dédoublonne les cues consécutives identiques (TikTok le fait)
    - rend un texte continu propre
    """
    lines: list[str] = []
    last = ""
    for raw in vtt_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(("WEBVTT", "NOTE", "STYLE")):
            continue
        if "-->" in line:
            continue
        # Les cues ont parfois une ID numérique seule sur une ligne.
        if line.isdigit():
            continue
        # Nettoie les balises VTT.
        line = re.sub(r"<[^>]+>", "", line)
        line = line.strip()
        if not line or line == last:
            continue
        lines.append(line)
        last = line
    return "\n".join(lines)


def srt_to_plain(srt_text: str) -> str:
    """Convertit un SRT en plain text (mêmes règles de nettoyage que vtt_to_plain)."""
    lines: list[str] = []
    last = ""
    for raw in srt_text.splitlines():
        line = raw.strip()
        if not line or line.isdigit() or "-->" in line:
            continue
        line = re.sub(r"<[^>]+>", "", line).strip()
        if not line or line == last:
            continue
        lines.append(line)
        last = line
    return "\n".join(lines)


def whisper_transcribe(video_path: Path, out_dir: Path) -> str | None:
    """
    Fallback Whisper FR :
        whisper <video> --language fr --output_format srt --output_dir <DIR>
    Retourne le transcript plain text, ou None si whisper absent / échec.
    """
    import shutil
    whisper_bin = shutil.which("whisper")
    if whisper_bin is None:
        print("[whisper] binaire introuvable — `pip install openai-whisper` pour activer le fallback",
              file=sys.stderr)
        return None
    print(f"[whisper] transcribing {video_path.name} (fr)…", file=sys.stderr)
    res = run([whisper_bin, str(video_path), "--language", "fr",
               "--output_format", "srt", "--output_dir", str(out_dir)])
    if res.returncode != 0:
        print("[whisper STDERR]\n" + res.stderr[-500:], file=sys.stderr)
        return None
    srt_path = out_dir / (video_path.stem + ".srt")
    if not srt_path.exists():
        print(f"[whisper] srt attendu introuvable : {srt_path}", file=sys.stderr)
        return None
    return srt_to_plain(srt_path.read_text(encoding="utf-8"))


def extract_frames(video_path: Path, frames_dir: Path, n: int, duration: float) -> list[Path]:
    """Extrait n frames espacées régulièrement (saute la 1ère et la dernière seconde)."""
    frames_dir.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []
    if duration <= 2:
        timestamps = [duration / 2]
    else:
        start, end = 1.0, max(1.0, duration - 1.0)
        step = (end - start) / max(1, n - 1)
        timestamps = [round(start + i * step, 2) for i in range(n)]
    for ts in timestamps:
        # Nom : frame_5p2s.jpg pour 5.2s
        label = str(ts).replace(".", "p")
        frame_path = frames_dir / f"frame_{label}s.jpg"
        cmd = ["ffmpeg", "-y", "-ss", str(ts), "-i", str(video_path),
               "-vframes", "1", "-q:v", "3", str(frame_path)]
        res = run(cmd)
        if res.returncode == 0 and frame_path.exists():
            out.append(frame_path)
        else:
            print(f"[ffmpeg] frame at {ts}s failed: {res.stderr[-200:]}", file=sys.stderr)
    return out


def virality_block(info: dict) -> str:
    """Construit un bloc Markdown 'stats virales' avec ratios calculés."""
    v = info.get("view_count")
    likes = info.get("like_count")
    shares = info.get("repost_count")
    comments = info.get("comment_count")

    def ratio(num, den):
        try:
            return f"{(num / den) * 100:.2f}%" if num is not None and den else "—"
        except Exception:
            return "—"

    lines = ["## Stats virales\n"]
    lines.append(f"- **Vues** : {v:,}".replace(",", " ") if isinstance(v, int) else "- Vues : —")
    lines.append(f"- **Likes** : {likes:,}".replace(",", " ") if isinstance(likes, int) else "- Likes : —")
    lines.append(f"- **Partages** : {shares:,}".replace(",", " ") if isinstance(shares, int) else "- Partages : —")
    lines.append(f"- **Commentaires** : {comments:,}".replace(",", " ") if isinstance(comments, int) else "- Commentaires : —")
    lines.append("")
    lines.append("### Ratios")
    lines.append(f"- shares/views : **{ratio(shares, v)}** (norme TikTok ~0.3-0.5% · >1% = tag-driven · >3% = exceptionnel)")
    lines.append(f"- likes/views : **{ratio(likes, v)}**")
    lines.append(f"- comments/views : **{ratio(comments, v)}**")
    return "\n".join(lines)


def write_summary(out_dir: Path, info: dict, subs_status: str, subs_lang: str | None,
                  subs_source: str | None, script: str, frames: list[Path]) -> Path:
    summary_path = out_dir / "summary.md"
    lines: list[str] = []
    title = (info.get("title") or "").strip()
    uploader = info.get("uploader") or info.get("channel") or "?"
    duration = info.get("duration")
    upload_date = info.get("upload_date") or "?"
    track = info.get("track") or "—"
    artist = info.get("artist") or "—"
    description = (info.get("description") or "").strip()
    webpage = info.get("webpage_url") or info.get("original_url") or "?"
    hashtags = info.get("hashtags") or re.findall(r"#\S+", description)

    lines.append(f"# {title[:200] or '(sans titre)'}")
    lines.append("")
    lines.append(f"- **URL** : {webpage}")
    lines.append(f"- **Uploader** : @{uploader}")
    lines.append(f"- **Durée** : {duration}s" if duration else "- Durée : ?")
    lines.append(f"- **Date upload** : {upload_date}")
    lines.append(f"- **Track** : {track} — {artist}")
    if hashtags:
        lines.append(f"- **Hashtags** : {' '.join(hashtags)}")
    lines.append(f"- **Sous-titres** : {subs_status}" + (f" ({subs_source}, {subs_lang})" if subs_lang else ""))
    lines.append("")
    lines.append(virality_block(info))
    lines.append("")
    lines.append("## Script (verbatim)")
    lines.append("")
    if script.strip():
        lines.append(script.strip())
    else:
        lines.append("_(aucun sous-titre dispo — fallback Whisper non lancé)_")
    lines.append("")
    if frames:
        lines.append("## Frames extraites")
        lines.append("")
        for f in frames:
            lines.append(f"- `{f.name}`")
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path


def main():
    ap = argparse.ArgumentParser(description="Extract transcript + frames + viral stats from a web video.")
    ap.add_argument("--url", required=True, help="Video URL (TikTok / YouTube / Reels / etc.)")
    ap.add_argument("--frames", type=int, default=8, help="Number of frames to extract (default: 8)")
    ap.add_argument("--out", required=True, help="Output directory (will be created)")
    ap.add_argument("--whisper", choices=["auto", "on", "off"], default="auto",
                    help="Fallback Whisper FR si pas de subs (auto, défaut) ; on = forcer ; off = jamais")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. yt-dlp download
    info = yt_dlp_download(args.url, out_dir)

    # 2. Subtitles
    subs_status = "none"
    subs_lang: str | None = None
    subs_source: str | None = None
    script = ""
    lang, source, sub_url = pick_subtitle_url(info)
    if sub_url:
        vtt_path = out_dir / f"subs.{lang}.vtt"
        if download_subs(sub_url, vtt_path):
            subs_lang = lang
            subs_source = source
            subs_status = "ok"
            script = vtt_to_plain(vtt_path.read_text(encoding="utf-8"))
            (out_dir / "script.txt").write_text(script, encoding="utf-8")
        else:
            subs_status = "url_found_but_download_failed"
    else:
        # Tente quand même de récupérer un VTT déjà écrit par yt-dlp (`--write-subs`).
        for p in out_dir.glob("video*.vtt"):
            subs_lang = p.suffixes[-2].lstrip(".") if len(p.suffixes) >= 2 else "unknown"
            subs_source = "yt-dlp-direct"
            subs_status = "ok"
            script = vtt_to_plain(p.read_text(encoding="utf-8"))
            (out_dir / "script.txt").write_text(script, encoding="utf-8")
            break

    # 3. Frames
    video_files = list(out_dir.glob("video.mp4")) or [p for p in out_dir.glob("video.*") if p.suffix.lower() in {".mp4", ".webm", ".mkv", ".mov", ".avi", ".ts"}]
    frames: list[Path] = []
    if video_files:
        video_path = video_files[0]
        duration = float(info.get("duration") or 0) or 30.0
        frames = extract_frames(video_path, out_dir / "frames", args.frames, duration)

    # 3bis. Fallback Whisper FR (auto si aucun sub trouvé, on = forcé, off = jamais)
    if video_files and (args.whisper == "on" or (args.whisper == "auto" and not script.strip())):
        whisper_script = whisper_transcribe(video_files[0], out_dir)
        if whisper_script and whisper_script.strip():
            script = whisper_script
            subs_status = "ok"
            subs_lang = "fr"
            subs_source = "whisper"
            (out_dir / "script.txt").write_text(script, encoding="utf-8")

    # 4. Summary
    summary_path = write_summary(out_dir, info, subs_status, subs_lang, subs_source, script, frames)

    # 5. Stdout JSON (utile si ce script est appelé depuis un pipeline)
    result = {
        "out_dir": str(out_dir),
        "summary": str(summary_path),
        "script": str(out_dir / "script.txt") if script else None,
        "frames": [str(f) for f in frames],
        "subtitles_status": subs_status,
        "subtitles_lang": subs_lang,
        "subtitles_source": subs_source,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
