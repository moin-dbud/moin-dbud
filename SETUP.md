# Setup

This turns your GitHub *profile* repo (the special one named exactly
your username, e.g. `moin-dbud/moin-dbud`) into a self-updating bento
stats card, built entirely by you instead of a third-party Action.

## 1. Drop the files in
Copy everything in this folder into the root of your `<username>/<username>`
repo, keeping the folder structure:
```
your-profile-repo/
├── .github/workflows/update-readme.yml
├── scripts/
│   ├── fetch_stats.py
│   ├── render_svg.py
│   ├── generate_bento.py
│   └── requirements.txt
├── assets/photo.jpg        <- put your own photo here
├── config.json
└── README.md
```

## 2. Add your photo
Put a `.jpg`/`.png` at `assets/photo.jpg` (or change `photo_path` in
`config.json`). It gets base64-embedded straight into the SVG, so no
external hosting or broken links.

## 3. Edit config.json
Set `github_login`, `display_name`, `tagline`, and up to 3 `tags`
(pills under the intro). Under `links`, fill in your `twitter`,
`linkedin`, and `website` handles/URLs — these are the labels shown
on the card (the URLs aren't clickable inside a raw SVG on GitHub, so
if you want them clickable, wrap the image in a markdown link in
`README.md`, e.g. `[![bento](bento.svg)](https://x.com/you)` — though
that makes the *whole* card one link, not per-card).

## 4. Create a token (only needed for private contribution counts)
The default `GITHUB_TOKEN` that Actions provides works fine for public
stats. If you want private repo contributions counted too:
1. GitHub → Settings → Developer settings → Personal access tokens →
   Fine-grained token (or classic with `read:user`, `repo` scopes).
2. In your profile repo: Settings → Secrets and variables → Actions →
   New repository secret → name it `BENTO_TOKEN`, paste the token.

The workflow already prefers `BENTO_TOKEN` if present and falls back
to the built-in token otherwise.

## 5. Enable Actions permissions
Repo → Settings → Actions → General → Workflow permissions →
**"Read and write permissions"**. (The workflow also declares
`permissions: contents: write` itself, but this repo-level toggle has
to allow it too, or the push step fails — this is the single most
common reason these bots fail.)

## 6. Run it
- Actions tab → "Update Bento README" → Run workflow (manual first run),
  or just wait for the daily cron (`17 5 * * *` UTC — edit the cron
  line in the workflow file if you want a different time).
- Check the Actions log if anything fails — the script prints each
  step (fetching, rendering, writing files) so the failure point is
  easy to spot.

## How daily updates actually land in the README
1. Cron fires → checkout → install deps.
2. `generate_bento.py` calls the GitHub GraphQL API for your live
   stats, builds a fresh `bento.svg`, and rewrites the content between
   `<!--BENTO:START-->` / `<!--BENTO:END-->` markers in `README.md`
   (everything outside those markers is left untouched, so you can
   write freely below them).
3. If `bento.svg` or `README.md` actually changed, the bot commits and
   pushes as `github-actions[bot]` — if nothing changed (e.g. you had
   no activity that day), it skips the commit so you don't get empty
   diffs every day.

## Debugging your current OpenBento failure
Since you already have OpenBento running, before switching over it's
worth a 2-minute check on why it's failing — open the failed run in
your Actions tab and look at which step is red. The two most common
causes for these bots:
- Workflow permissions not set to "Read and write" (see step 5 above).
- The token used has expired or lacks the scope OpenBento's workflow
  expects for private-contribution stats.
If it's one of those, you may not need to rebuild at all.
