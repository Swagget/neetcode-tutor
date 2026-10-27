---
description: One graduated hint for a problem I'm stuck on (URL or slug) - never code, never the solution
argument-hint: <problem-url>
---
I'm stuck on the problem at: $ARGUMENTS
Don't show solutions or code. Give ONE hint per message, escalating only when I ask for the next:
1) what the constraints suggest, 2) which pattern, 3) the key observation, 4) the approach in plain words.
Check the Claude Insights page first. If I'm likely heading into one of my known traps, nudge me with a question instead of a statement.

How:
- Slug: `uv run python slug_from_url.py <url>`. Problem statement, constraints and topics: `uv run python problem_info.py <slug>` (read-only; do not scrape submissions).
- Insights page: notion-fetch https://app.notion.com/p/aniketwagde/Claude-Insights-40654c1b345a8027ac8aeaa3d5700a1a
- Track the hint level for this slug within the conversation: first call = level 1, each further call for the same slug goes up one. After level 4, say the next step is to attempt it and run /tutor afterwards.
- 1 to 3 lines per hint, phrased as a question or nudge when possible.
