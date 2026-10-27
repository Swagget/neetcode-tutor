---
description: Post-solve tutoring on one problem (URL or slug, optional recording path) - one root cause, Socratic, writes the tip
argument-hint: <problem-url> [recording-path]
---
Tutor me on the problem at: $ARGUMENTS
(The first argument is the problem URL; an optional second argument is a recording path.)
Follow CLAUDE.md: short messages, teach the idea not the history, one root cause.

1. Get the slug: `uv run python slug_from_url.py <url>`. Run `uv run python scrape.py --slugs <slug>` (if it prints SESSION EXPIRED, ask me to run `uv run python login.py` and stop). Read my submissions (`out/<slug>.md`), my Notion notes (`uv run python notion_sync.py show <slug>`), and the Claude Insights page (notion-fetch https://app.notion.com/p/aniketwagde/Claude-Insights-40654c1b345a8027ac8aeaa3d5700a1a).
2. Recording: find it (see CLAUDE.md "Recordings": given path, else the newest file in recordings/ modified in the last 6 hours whose hash is not in transcripts/.cache.json, and confirm the filename with me first). Run `uv run python transcribe.py <file> --slug <slug>` and read the transcript. From it, work out:
   - My reasoning timeline: when I picked an approach, when I changed course, where I went silent or circled.
   - The moment my thinking went off track, with a timestamp and a short quote.
   - Whether what I SAID matches what I CODED (e.g. I said O(n) but wrote nested loops).
   - Interview communication, scored briefly (✅/⚠️/❌): clarified the problem? walked an example? stated brute force + complexity before optimizing? explained the plan before coding? traced/tested at the end? narrated or went silent?
3. Before explaining anything, ask me 1-2 short questions. If there's a recording, anchor them to it ("At 04:10 you said X. What made you drop it?"). Wait for my answer.
4. Find the ONE root cause: the gap between my framing and what the clean solution needed.
5. Teach Socratically: ask one guiding question toward the key insight and let me answer. Max 2 rounds, then explain directly in ≤5 lines.
6. If there's a recording, give speaking feedback in ≤4 lines: the communication scorecard from step 2 plus ONE thing to do differently out loud next time, as a sentence I could actually say ("Before I code, the brute force is O(n³) because...").
7. If this matches a trap on the Insights page (clusters in data/insights_clusters.json), say so: "Same trap as <problem>."
8. Show me the tip (CLAUDE.md format, including 🗣️ if there was a recording). After I OK it: write out/tips/<slug>.txt, run `uv run python merge_tips.py <slug>` (must pass), then `uv run python notion_sync.py write-tips --only <slug> --create-missing`. Also write the long-form analysis to out/tips_verbose/<slug>.txt and out/tips_verbose/tips_verbose.json and push it with `uv run python notion_sync.py write-tips --prop "claude tips (verbose)" --tips out/tips_verbose/tips_verbose.json --only <slug>`. Add the slug to its cluster in data/insights_clusters.json. If a trap now appears in ≥2 problems, update the Insights page by editing lines (notion-update-page update_content), never appending paragraphs.
9. Suggest 1 follow-up problem (with URL) that drills the same idea.

Never edit My intuition / What I missed / Bullet Points Refresher. Never submit or run anything on NeetCode.
