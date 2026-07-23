# Cryptobead Content Repo

This repo holds ONLY automated content and the scripts that generate it.
Your actual website design/code lives in a separate repo connected to Cloudflare.

## Folder structure
- `news/articles.json` - list of all published articles (site fetches this via jsDelivr)
- `news/images/` - cover images for articles
- `news/pending_topics.json` - today's researched topics waiting to be written
- `news/author_rotation.json` - tracks which author writes each of the day's 5 slots
- `guides/guides.json` - list of all published guides
- `automation/` - the Python scripts that do the writing
- `.github/workflows/` - the schedules that run those scripts automatically

## Required GitHub Secrets (Settings -> Secrets and variables -> Actions)
- `GEMINI_API_KEY`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

## Required repo setting
Settings -> Actions -> General -> Workflow permissions -> set to
"Read and write permissions" or the automated commits will fail.

## Author rotation
5 daily article slots. Slot 1 and slot 4 go to Aishat Abubakar. Slots 2, 3, and 5
rotate in strict order through the other 5 authors (no randomness), so everyone
gets an even number of turns over time.

## Daylight Saving Time reminder
Schedules are set for US Eastern Time assuming EDT (UTC-4), correct roughly
mid-March to early November. When the US switches back to EST (UTC-5) in
November, every cron time in the 3 workflow files needs to shift ONE HOUR
EARLIER in UTC terms to keep firing at the same actual Eastern time.
