# NeetCode tutor

## What this repo is
My NeetCode submission backup + a tutor that helps me learn from each problem for Google interviews.
What matters: recognizing the pattern fast, framing the problem cleanly, avoiding my recurring traps.
- scrape.py: pulls my submissions (--slugs, --since). Accepts URLs via slug_from_url. Merges into out/submissions.jsonl and writes out/<slug>.md.
- notion_sync.py: writes to the Notion "Neetcode" database (collection://3e454c1b-345a-8014-b859-000b6fecbab7), property "claude tips" (and "claude tips (verbose)" with --prop). `notion_sync.py show <slug>` prints my notes, current tip and submission summary.
- merge_tips.py: validates out/tips/<slug>.txt against the tip format and builds out/tips.json (`--check` = validate only).
- transcribe.py: turns my think-aloud recordings (recordings/) into timestamped transcripts (transcripts/). faster-whisper large-v3 on CUDA; `--latest` picks the newest recording.
- problem_info.py <slug>: problem statement, difficulty, topics (read-only).
- data/insights_clusters.json: which problems carry which trap; drives the Insights page ranking.
- Claude Insights page (my one-screen playbook): https://app.notion.com/p/aniketwagde/Claude-Insights-40654c1b345a8027ac8aeaa3d5700a1a

## Commands
- /hint <url>: graduated hints while I'm stuck
- /tutor <url> [recording]: post-solve tutoring, using my recording if there is one
- /review: weekly refresh of the Insights page + redo picks
Arguments are problem URLs (NeetCode or LeetCode); convert with slug_from_url (`uv run python slug_from_url.py <url>`).

## Recordings
I practice speaking out loud while solving, like in a real interview. If /tutor gets no recording path, use the newest file in recordings/ modified in the last 6 hours that hasn't been transcribed yet (transcripts/.cache.json maps file hashes to transcripts), and confirm the filename with me before using it. If there's none, tutor from submissions alone.

## Writing rules (always)
- Teach the idea, not the history. Never narrate attempts ("Attempts 4 to 9...").
- One root cause per problem, not a bug list.
- Short lines, plain words. Messages to me are a few lines, not essays.
- Every lesson must transfer to other problems.
- When quoting my recording, quote a short phrase with its timestamp, never long passages.

## Tip format ("claude tips" property, ≤45 words, ≤57 with the speaking line)
🔑 Key idea: <insight that cracks it, ≤12 words>
⚠️ My trap: <my root-cause mistake, ≤12 words>
❓ Next time ask: <interview self-question, ≤12 words>
🗣️ Say it: <one speaking habit to fix, ≤12 words> (only when a recording was used)

Example (Design Linked List):
🔑 Key idea: Dummy head/tail sentinels make every insert/delete one code path.
⚠️ My trap: Patched edge cases one at a time instead of fixing the design.
❓ Next time ask: Can a sentinel remove my special cases?

Workflow: write out/tips/<slug>.txt, `uv run python merge_tips.py <slug>` must pass, then
`uv run python notion_sync.py write-tips --only <slug> --create-missing`.
The long-form analysis (3-6 "• " bullets) goes to out/tips_verbose/<slug>.txt and out/tips_verbose/tips_verbose.json, pushed with
`uv run python notion_sync.py write-tips --prop "claude tips (verbose)" --tips out/tips_verbose/tips_verbose.json --only <slug>`.

## Never
- Edit My intuition / What I missed / Bullet Points Refresher (those are mine).
- Submit, run, or change anything on NeetCode. Only scrape.py and problem_info.py talk to it, read-only.
- Ask for or store my NeetCode credentials; login.py lets me sign in myself (re-run it when scrape.py says SESSION EXPIRED).
- Commit recordings or transcripts (recordings/ and transcripts/ are gitignored), or auth/, out/, .env.
- Let the Claude Insights page grow past about one screen; update it by editing lines, not appending paragraphs.
