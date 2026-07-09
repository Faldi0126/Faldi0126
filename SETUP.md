# Setup guide

This turns the Fast26-styled card into a live profile that refreshes on its own.
Follow it once, then never touch it again.

## What you're setting up

- `generate.py` fetches your GitHub stats and writes one SVG.
- A GitHub Action runs it once a week and commits the fresh SVG back.
- Your profile README embeds that SVG.

## Step 1 — create the special repo

GitHub treats a repo named exactly like your username as your profile page.

1. Make a new **public** repo named `Faldi0126` (must match your username exactly).
2. When GitHub offers it, tick "Add a README file", or just push the files below.

## Step 2 — add these files to the repo

Copy the whole folder in. Your repo should look like this:

```
Faldi0126/
  README.md
  generate.py
  SETUP.md
  fonts/
    sora-500.woff2
    jakarta-400.woff2
    jakarta-600.woff2
  dist/
    profile-card.svg
  .github/
    workflows/
      profile-card.yml
```

The `dist/` SVG is already generated with sample numbers, so your profile
looks right the moment you push, before the first scheduled run.

## Step 3 — let the Action write to your repo

1. In the repo, go to **Settings → Actions → General**.
2. Scroll to **Workflow permissions**.
3. Select **Read and write permissions**, then save.

That's what lets the weekly job commit the updated card.

## Step 4 (optional) — richer stats with a personal token

The built-in token covers your public repos already. If you want the full
contribution calendar and private-repo commit totals folded in:

1. Create a token at **github.com → Settings → Developer settings →
   Personal access tokens → Fine-grained tokens**.
   Give it read access to your repositories and to your profile/read stats.
2. In the profile repo, go to **Settings → Secrets and variables → Actions →
   New repository secret**.
3. Name it `PROFILE_TOKEN` and paste the token.

The workflow uses it automatically if present, and ignores this step if not.

## Step 5 — run it once by hand

1. Go to the **Actions** tab.
2. Pick **Refresh profile card** on the left.
3. Click **Run workflow**.

It regenerates the card with your real numbers and commits them. Refresh your
profile page and you'll see it.

## Changing your name or tagline

Edit the `DISPLAY_NAME` and `TAGLINE` lines in
`.github/workflows/profile-card.yml`. The next run picks them up.

## Changing the "Most Used" stack or your start date

The stack is a hand-picked list, not something the API infers. Edit the `TECH`
list in `generate.py` — each entry pairs a label with a small icon-drawing
function right above it. Years of experience counts up from `CAREER_START` in
the same file.

## Running locally to preview

```bash
GH_TOKEN=your_token GH_USERNAME=Faldi0126 python generate.py
```

With no token it uses sample numbers, so you can still preview the design.

## Troubleshooting

- **Card doesn't update:** check the Actions tab for a failed run. The most
  common cause is skipping Step 3 (write permissions).
- **Fonts look wrong:** make sure the whole `fonts/` folder was committed. The
  SVG embeds them, so they can't be missing.
- **Stale card shows:** GitHub caches SVGs hard. Wait a few minutes, or append
  `?v=2` to the image path in the README to bust the cache once.
