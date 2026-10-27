---
description: Weekly review - refresh the Claude Insights page, draft tips for new problems, pick 3 to redo out loud
---
Weekly review. Follow CLAUDE.md writing rules; keep messages short.
1. Run `uv run python scrape.py --since <7 days ago, YYYY-MM-DD>` (if SESSION EXPIRED, ask me to run `uv run python login.py` and stop), then `uv run python notion_sync.py dump-rows`. For new problems that lack a tip (in data/notion_rows_full.json the "tips" field is empty, or the slug is missing from out/tips.json), draft 3-line tips and ask me before writing them (then the usual merge_tips.py + notion_sync.py write-tips --only ... --create-missing).
2. Read this week's transcripts (transcripts/*.md dated this week, if any) for speaking patterns across problems.
3. Refresh the Claude Insights page (notion-fetch, then notion-update-page update_content, editing lines in place), keeping it to about one screen:
   - My top 5 traps: trap → one-line fix → 2-3 example problems. Add this week's problems to their cluster in data/insights_clusters.json (by their ⚠️ line), re-rank by size, swap a trap in only if it displaced one.
   - Pattern cue cards: "When I see ___ → think ___", 🔴 on patterns I struggle with (not accepted first try this week, or rated Struggling / A bit confused).
   - Interview checklist: ≤7 self-questions, in order clarify → examples → frame → approach → code → trace.
   - Speaking habits: my top 3 communication gaps from recordings, each with a sentence to say instead.
   - Progress: one line for this week (count, fading traps, new traps, communication trend). Replace this week's line if it exists.
4. Pick 3 problems for me to redo from memory, out loud, where a trap still recurs (prefer Struggling / A bit confused, spread across patterns). Give their URLs and the ❓ line from each tip, one line each.

Never edit My intuition / What I missed / Bullet Points Refresher.
