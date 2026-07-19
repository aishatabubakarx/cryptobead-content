# Cryptobead Content Repo

This repo holds ONLY automated content and the scripts that generate it.
Your actual website design/code lives in a separate repo connected to Cloudflare Pages.

## Folder structure
- `news/articles.json` — list of all published articles (your site's frontend fetches this)
- `news/images/` — cover images for articles
- `news/pending_topics.json` — today's researched topics waiting to be written (auto-managed)
- `guides/guides.json` — list of all published guides
- `automation/` — the Python scripts that do the writing
- `.github/workflows/` — the schedules that run those scripts automatically

## Required GitHub Secrets (Settings → Secrets and variables → Actions)
- `GEMINI_API_KEY`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

## Daylight Saving Time reminder
The workflow schedules are set for US Eastern Time assuming EDT (UTC-4), which is
correct roughly mid-March to early November. When the US switches back to EST (UTC-5)
in November, every cron time in the 3 workflow files needs to shift ONE HOUR EARLIER
in UTC terms (e.g. '0 12 * * *' becomes '0 13 * * *') to keep firing at 8am Eastern.
Set a reminder for the first Sunday of November and the second Sunday of March each year.
