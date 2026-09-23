# KebabTV

Two parts:

- `bot/` pulls every video from https://www.youtube.com/@KEBABTVKBH (info, Danish subtitles, comments, thumbnail). Claude (via Moodly) reads each one and pulls out the place, address, score, quotes and what viewers think. Results go to `site/src/data/`.
- `site/` is the website (Astro). It is built from those JSON files.

## First time

```
python -m pip install -r bot/requirements.txt
cd site
npm install
```

Put your Moodly key in `.env` in this folder:

```
MOODLY_API_KEY=your-key
```

## Update with new videos

```
python bot/run.py
```

This only works on new videos. Old ones are cached in `data/raw/`, so a re-run is cheap.

Options:

| Command | What it does |
|---|---|
| `python bot/run.py --limit 3` | Test on the 3 newest videos |
| `python bot/run.py --no-llm` | Download only, no AI (free) |
| `python bot/run.py --force analyze` | Redo the AI review step for all videos |
| `python bot/run.py --only VIDEO_ID` | Run one video |
| `KEBAB_MODEL=claude-sonnet-5 python bot/run.py` | Use a cheaper model |

## Website

```
cd site
npm run dev      # live preview at http://localhost:4321
npm run build    # static site in site/dist/, upload anywhere (Netlify, Vercel, GitHub Pages)
```

Pages: `/` (TV + remote), `/hitlisten`, `/kortet`, `/sted/<name>`, `/oensker`, `/tekst-tv`.
