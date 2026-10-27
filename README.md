# NeetCode -> Notion submission backup and tips

Backs up every NeetCode submission (code + status + failing test case) and writes Claude-written
coaching tips into the "claude tips" property of the Notion "Neetcode" database.

## One-time setup
- `uv sync` then `uv run playwright install chromium`
- `.env` with `NOTION_TOKEN=ntn_...` (integration must be connected to the database)
- `uv run python login.py` : opens a headed browser, you sign in to NeetCode manually, session is
  saved to `auth/neetcode_state.json` (Firebase token lives in IndexedDB). Re-run when scrape.py
  reports SESSION EXPIRED.

## Record → drop → /tutor
1. Solve a problem on NeetCode while talking out loud, recording yourself (phone voice memo, OBS, anything: m4a, mp3, wav, webm, mp4).
2. Drop the file in `recordings/` (gitignored, private).
3. In Claude Code run `/tutor <problem-url>`; it picks the newest untranscribed recording (confirms the filename with you),
   transcribes it locally on the GPU (`transcribe.py`, faster-whisper large-v3, nothing leaves the machine),
   asks what you tried, finds the one root cause, scores your interview communication, and writes the tip to Notion.
   Transcripts land in `transcripts/<slug>_<date>.md` with timestamps and `[PAUSE m:ss]` markers.
4. No recording? `/tutor <url>` works from submissions alone. Stuck mid-problem? `/hint <url>`. Weekly: `/review`.

## Tutor workflow (daily use, in Claude Code)
- Stuck mid-problem: `/hint <slug>` gives one graduated hint per call (constraints → pattern → key observation → approach). Never code.
- Just finished a problem: `/tutor <slug>` scrapes your submissions, asks what you tried, diagnoses the one root cause Socratically,
  writes the 3-line tip (🔑 Key idea / ⚠️ My trap / ❓ Next time ask) to Notion, updates the Insights page if a trap recurs, suggests one follow-up.
- Weekly: `/review` refreshes the Claude Insights page (top traps, pattern cue cards, checklist, progress line) and picks 3 problems to redo.
- Rules every session follows are in `CLAUDE.md`; the Insights page: https://app.notion.com/p/aniketwagde/Claude-Insights-40654c1b345a8027ac8aeaa3d5700a1a
- Long-form analyses live in `out/tips_verbose/` and in the Notion property "claude tips (verbose)"; the 3-line tip is in "claude tips".

## Re-run for new problems (manual, if you bypass /tutor)
```
uv run python scrape.py --since 2026-10-27        # merges new submissions into out/submissions.jsonl + out/<slug>.md
uv run python notion_sync.py dump-rows            # refresh data/notion_rows_full.json (your notes)
uv run python build_tipwork.py 1                  # bundles -> out/tipwork/<slug>.md
#   write tips for the new slugs into out/tips/<slug>.txt (ask Claude; style rules in the Agent brief / existing files)
uv run python merge_tips.py                       # validates -> out/tips.json
uv run python notion_sync.py plan                 # preview
uv run python notion_sync.py write-tips --create-missing
uv run python verify.py                           # Notion vs source, live spot-check, idempotency
```
`scrape.py` with no flags re-scrapes everything (Notion URL column + all NeetCode-completed problems).
`--all-neetcode` also probes every NeetCode slug to find attempted-but-never-accepted problems.

## Files
- `scrape.py` : NeetCode scraper (read-only; uses `/api/getProblemMetadataFunctionHttp` with the Firebase bearer token)
- `notion_sync.py` : Notion API client. Only ever writes the `claude tips` property (and fills an empty URL for aliased rows); creates rows for problems with no row.
- `notion_md.py` : older renderer for page-body sections (unused now, kept for reference)
- `data/notion_rows*.json`, `out/` : local data (out/ and auth/ are gitignored)
