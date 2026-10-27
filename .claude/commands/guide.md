---
description: Quick-start for this repo - the record → drop → /tutor workflow, what each command does, how to re-scrape
---
Print a quick-start for this repo in at most 12 lines. Read CLAUDE.md and README.md first and take every path, flag and command name from them, so the guide stays accurate when they change. Do not run any scripts.

Cover, in this order, one line each unless noted:
1. The daily loop: record yourself solving out loud → drop the file in recordings/ → run /tutor <url>.
2. /hint <url>: one graduated hint per call while stuck, never code.
3. /tutor <url> [recording]: post-solve tutoring from submissions and (if present) the recording; writes the tip to Notion.
4. /review: weekly refresh of the Claude Insights page plus 3 problems to redo out loud.
5. Re-scraping new submissions manually (the scrape.py command with --since or --slugs, and login.py if the session expired).
6. A reminder to run /review once a week.

Plain lines, no headers, no essay. If something in CLAUDE.md or README.md contradicts this list, follow the files.
