"""Print a NeetCode problem's statement, difficulty and topics (read-only API call, no submission data).

Usage: uv run python problem_info.py <slug> [--full]
Used by /hint so Claude can hint without the user pasting the problem.
"""
import asyncio, json, re, sys
from playwright.async_api import async_playwright
from scrape import Client, STATE, BASE, AuthExpired


async def main():
    if len(sys.argv) < 2:
        sys.exit("usage: problem_info.py <slug> [--full]")
    slug, full = sys.argv[1], "--full" in sys.argv
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(storage_state=str(STATE))
        page = await ctx.new_page()
        await page.goto(BASE + "/", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        client = Client(page, 1)
        try:
            d = (await client.call("/api/getProblemMetadataFunctionHttp", {"problemId": slug})).get("data") or {}
        except AuthExpired as e:
            sys.exit(f"SESSION EXPIRED: {e}")
        await browser.close()
    if not d:
        sys.exit(f"no such problem: {slug}")
    desc = d.get("description", "")
    desc = re.sub(r"<details.*", "", desc, flags=re.S).strip()  # drop the collapsed hint/topic HTML
    print(f"# {d.get('name')}  [{d.get('difficulty')}]  topics: {', '.join(d.get('topics') or [])}")
    print(f"completed by user: {d.get('completed')}   submissions on record: {len(d.get('submissionHistory') or [])}")
    print()
    print(desc if full else desc[:2500])
    sc = (d.get("starterCode") or {}).get("python")
    if sc:
        print("\nstarter code (python):\n" + sc)


asyncio.run(main())
