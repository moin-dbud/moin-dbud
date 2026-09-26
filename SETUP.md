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
Two options, tried in this order:
- **`photo_url`** (recommended, since you have a portfolio site): set it in
  `config.json` to a direct link to the image (e.g.
  `https://yoursite.com/photo.jpg` — the URL has to resolve straight to the
  image bytes, not an HTML page). The workflow downloads it fresh each run
  and embeds it as base64, so the card never depends on the other site
  being reachable at *viewing* time, only at *build* time.
- **`photo_path`**: falls back to a local file (e.g. `assets/photo.jpg`)
  if `photo_url` is empty or the download fails for any reason — the run
  won't fail, it just falls back silently (a warning gets printed to the
  Actions log). Any extension in `assets/` matching the filename works,
  so a `.jpg` vs `.png` mismatch can't break it.

## 3. Edit config.json
Set `github_login`, `display_name`, `tagline`, and up to 3 `tags`
(pills under the intro). Under `links`, fill in your `twitter`,
`linkedin`, and `website` handles/URLs — these are the labels shown
on the card (the URLs aren't clickable inside a raw SVG on GitHub, so
if you want them clickable, wrap the image in a markdown link in
`README.md`, e.g. `[![bento](bento.svg)](https://x.com/you)` — though
that makes the *whole* card one link, not per-card).

## 4. Create your token — REQUIRED (not optional)
This is the fix for the "my numbers don't match my real GitHub profile"
bug: the scripts query GitHub's API as `viewer` (i.e. "whoever this
token belongs to") instead of `user(login: ...)`, because GitHub's API
silently drops private-repo contributions from the `user(login:)` form
— even with "Include private contributions" on in your settings — with
no error, just a smaller number. `viewer` returns your true, complete
graph, but only if the token actually belongs to you.

**This means the default `GITHUB_TOKEN` Actions provides can no longer
be used** — it represents the `github-actions` bot, not you, so
`viewer` would resolve to the bot's own (empty) activity. You must set
up a personal token:
1. GitHub → Settings → Developer settings → Personal access tokens →
   generate one with `read:user` and `repo` scopes (classic PAT is
   simplest). If you use a **fine-grained** PAT instead, set its
   repository access to **"All repositories"** — scoping it to only
   some repos silently drops activity on the rest, the same failure
   mode as the bug this fixes.
2. In your profile repo: Settings → Secrets and variables → Actions →
   New repository secret → name it `BENTO_TOKEN`, paste the token.

If `BENTO_TOKEN` is missing or wrong, the run now **fails loudly** with
a specific error in the Actions log (which token/scope is missing, or
whose account the token actually belongs to) instead of silently
publishing undercounted stats like before.

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

## If your stats look lower than your real GitHub profile
This was an actual bug, not a misconfiguration on your end — see step 4
above for the full explanation and fix. Quick version: if `github_login`
in `config.json` doesn't match the account `BENTO_TOKEN` belongs to (or
`BENTO_TOKEN` isn't set at all), the Actions run now fails with a clear
error telling you exactly which of those is wrong, rather than quietly
publishing undercounted numbers. If a run from before this fix already
published a wrong `bento.svg`, just re-run the workflow once the token
is set up correctly and it'll overwrite it with the real numbers.

## Debugging your current OpenBento failure
Since you already have OpenBento running, before switching over it's
worth a 2-minute check on why it's failing — open the failed run in
your Actions tab and look at which step is red. The two most common
causes for these bots:
- Workflow permissions not set to "Read and write" (see step 5 above).
- The token used has expired or lacks the scope OpenBento's workflow
  expects for private-contribution stats.
If it's one of those, you may not need to rebuild at all.

## Design notes (gradients, glow, motion)
- Every card uses a diagonal brand-color → near-black gradient plus a
  soft blurred "glow" blob clipped to its rounded corners, instead of
  a flat solid fill.
- Motion is done with native SVG/SMIL (`<animate>`, `<animateTransform>`),
  not JavaScript — GitHub's markdown sanitizer strips `<script>` tags
  from embedded SVGs but leaves SMIL animation elements alone (this is
  the same mechanism the popular "readme-typing-svg" project relies on,
  so it's a well-trodden, reliable path). On load: the heatmap sweeps in
  column-by-column, the commits sparkline draws itself in, and the
  activity bars grow up — all one-time and settle ("freeze") into their
  final state within about 1.5s. The streak flame and the two hero
  numbers (Total Stars, Current Streak) keep a gentle continuous pulse.
  If a future GitHub sanitizer update ever did strip these, the cards
  degrade gracefully to their static end-state — nothing breaks.
- A static image viewer (like opening the `.svg` file directly in some
  tools) may not animate at all and can show the *pre-animation* frame
  (e.g. bars flat, heatmap blank) since it doesn't execute SMIL — this
  is a viewer limitation, not a bug; GitHub's own rendering (a browser)
  handles it correctly.
