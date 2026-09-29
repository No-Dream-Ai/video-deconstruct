---
name: video-deconstruct
description: Extrait le transcript + frames + stats virales d'une vidéo en ligne (TikTok, YouTube, YouTube Shorts, Instagram Reels, X/Twitter, Facebook, etc.) pour la décortiquer et s'en inspirer. Triggers — "récupère le script de cette vidéo", "extrait le transcript", "que dit cette vidéo TikTok/YouTube/Reels/Shorts", "donne-moi les frames de cette vidéo", "décortique cette vidéo virale", "analyse cette vidéo", "comment marche ce TikTok", "tu peux récupérer la transcription", URL de TikTok / YouTube / Instagram / X dans le message. NE PAS utiliser pour générer du contenu nouveau, ni pour scraper une page web non-vidéo (WebFetch classique suffit). Limite : si la vidéo n'a NI subs auto NI subs manuels, extract.py lance automatiquement un fallback Whisper FR (flag --whisper auto/on/off ; nécessite openai-whisper installé).
license: Internal use
---

# Video Deconstruct — Extract transcript + frames + viral stats

## Quand l'invoquer

- L'utilisateur partage une URL de vidéo (TikTok, YouTube, Shorts, Reels, X/Twitter video, etc.) et veut comprendre/analyser ce qui s'y passe
- Demande explicite de "le script", "le transcript", "ce qui est dit", "les frames", "voir la vidéo" sur un lien
- Préparation d'une analyse virale ou d'une transposition créative
- Recherche concurrentielle de contenu court-format

**NE PAS utiliser pour** :
- Générer du nouveau contenu (ce skill EXTRAIT, il ne produit pas)
- Scraper une page web non-vidéo (utiliser un fetch HTTP classique)
- Lire les commentaires/réactions sociales (yt-dlp ne les sort pas)
- Vidéos derrière paywall, comptes privés, géo-bloquées (yt-dlp échouera)

## Pourquoi ce skill existe

Les fetchers HTTP classiques renvoient une page vide sur TikTok / Instagram / YouTube Shorts (rendu côté client + anti-bot). La seule voie fiable est `yt-dlp` (≈1000 sites supportés, mis à jour quasi-quotidiennement). Ce skill mécanise le process pour ne plus avoir à le redécouvrir à chaque vidéo.

## Prérequis (à installer une fois)

```bash
pip install --user yt-dlp
ffmpeg -version          # doit être dans le PATH
```

Si `yt-dlp` n'est pas dans le PATH, utiliser `python -m yt_dlp` (équivalent, marche toujours).

Optionnel (fallback transcription si la vidéo n'a aucun sous-titre) :
```bash
pip install --user openai-whisper
```

## Workflow

Le script `extract.py` (fourni dans ce dossier) automatise tout. Une seule commande suffit :

```bash
PYTHONIOENCODING=utf-8 python extract.py \
  --url "<URL_VIDÉO>" \
  --frames 8 \
  --out "<dossier_de_sortie>/<slug>"
```

> Sous Windows, exécuter via un shell type git-bash plutôt que PowerShell pour la variable d'env `PYTHONIOENCODING`. Équivalent PowerShell : `$env:PYTHONIOENCODING="utf-8"; python extract.py --url "<URL_VIDÉO>" --frames 8 --out "<dossier>/<slug>"`

Le script :
1. Télécharge la vidéo (mp4) + metadata (video.info.json) + description (video.description) via yt-dlp
2. Tente de récupérer les subs FR (manuels d'abord, puis auto) ; fallback EN si pas de FR ; échec silencieux sinon
3. Parse le VTT en plain text (sans timestamps) et sauvegarde `script.txt`
4. Extrait N frames espacées régulièrement via ffmpeg → `frames/frame_<ts>s.jpg`
5. Écrit `summary.md` lisible (titre, uploader, durée, vues, likes, shares, comments, track, hashtags, script, liste frames)

**Output dir** : un dossier par vidéo. Convention `<sortie>/<slug>` où `<slug>` = `<uploader>_<video_id_court>`.

## Que faire après l'extraction

1. **Lire `summary.md`** pour stats virales + transcript verbatim — c'est l'output principal
2. **Lire les frames** une par une (les .jpg s'affichent comme images si votre outil le permet) — donne le visuel/setup/sous-titres/persos
3. **Restituer** en deux temps : (a) l'EXTRACTION brute (script verbatim + stats avec ratios — shares/views est le KPI clé : >1% = tag-driven, >3% = exceptionnel — + visuel frame par frame), puis (b) le DÉCORTICAGE narratif selon la grille à 6 axes ci-dessous + la timeline payoff↔timestamp.

## Grille de décorticage narratif (6 axes)

> Réflexe : on ne cherche pas SI « c'est bien fait », on cherche QUOI est fait et COMMENT — pour comprendre le mécanisme, pas pour copier verbatim.

**Axe 1 — TITRE / première frame = hook ?** Le titre source (et le texte overlay de la 1re frame) pose-t-il un **quoi improbable** en cachant le **comment** ? Patrons fréquents : trait-paradoxe / superlatif, résultat improbable sans spoiler, question candide chiffrée. Ou au contraire titre-résumé plat, power-word creux, spoiler de la fin ?

**Axe 2 — HOOK (0-3s).** Entrée par la fascination (fait brutal avant date/lieu, résultat-avant-récit) ou par le sujet ("aujourd'hui on va parler de…") ? Une boucle/promesse est-elle plantée d'entrée ? Curiosité = vrai paradoxe ou clickbait artificiel ("reste jusqu'au bout") ?

**Axe 3 — STRUCTURE macro (escalade par paliers).** Le milieu est-il un escalier (chaque palier surenchérit) ou une plaine (liste plate) ? Compter les paliers croissants et le couronnement. Repérer le moteur à problèmes, les fausses résolutions, l'éventuel récap de milieu.

**Axe 4 — CADENCE (densité de payoff).** Rythme des relances : combien de phrases factuelles d'affilée avant une intervention de la voix (réaction, question, surenchère, comparaison) ? Repère usuel : jamais plus de 3 phrases nues / 25s. Zones de plat (ventre-mou) ? Où ?

**Axe 5 — MÉCANIQUES de payoff + TRANSITIONS.** Typer les relances : question rhétorique → réponse-punch ; fausse alternative raisonnable → chute absurde ; surenchère "et le pire ?" ; fausse fin / faux espoir contredit ; cliffhanger interne planté tôt, payé tard. Relever l'arsenal de transitions orales ("sauf que", "le problème c'est que", "et c'est là que", "devinez quoi", "bref").

**Axe 6 — FIN (boucle + dernière phrase).** La promesse-boucle du hook est-elle refermée en quasi-verbatim (effet Zeigarnik) ? L'outro porte-t-elle une dernière phrase distincte du CTA ?

**+ Livraison des faits.** Chaque chiffre/fait est-il livré nu (encyclopédique) ou digéré (recadrage à échelle humaine, conversion d'époque, comparaison-choc) ? C'est la digestion qui rend viral, pas le chiffre nu.

## Timeline payoff ↔ timestamp + courbe de tension

Produire un mapping timestamp → événement narratif (croiser le script et les frames horodatées). Exemple de sortie :

```
0:00  HOOK — fait brutal (résultat avant récit)         [tension haute]
0:08  palier 1 + question rhétorique → punch            [↑]
0:19  fait digéré (comparaison-choc)                     [→]
0:27  fausse fin contredite ("sauf que")                 [↑↑]
0:41  ZONE DE PLAT — 4 phrases nues, aucun payoff        [↓ ventre-mou]
0:58  couronnement + callback verbatim du hook           [pic]
```

Objectif : visualiser où le créateur tient l'attention et où il décroche.

## Limites connues

- **Pas de subs ni auto ni manuels** : `extract.py` lance automatiquement le fallback Whisper FR quand `subtitles_status=none` et que `whisper` (openai-whisper) est installé. Flag `--whisper {auto,on,off}` : `auto` (défaut) = seulement si aucun sub ; `on` = forcer même si des subs existent ; `off` = jamais.
- **TikTok impersonation warning** : yt-dlp affiche `WARNING: [TikTok] The extractor is attempting impersonation, but no impersonate target is available`. C'est OK — le download passe quand même. Pour éliminer le warning : `pip install --user "yt-dlp[default,curl-cffi]"`.
- **Vidéos longues (>15 min)** : 8 frames ne suffisent pas pour cartographier le visuel. Augmenter `--frames 20`.
- **Comptes/posts privés, géo-bloqués** : yt-dlp échouera avec un message explicite. Pas de contournement propre depuis ce skill.

## Exemples (formulations qui doivent déclencher ce skill)

- "tu peux récupérer le script de cette vidéo https://www.tiktok.com/..."
- "extrait le transcript et 10 frames de https://www.youtube.com/shorts/..."
- "décortique ce TikTok pour moi : https://..."
- "que dit cette vidéo : https://www.instagram.com/reel/..."
- "donne-moi les frames de cette vidéo X : https://x.com/.../status/..."
