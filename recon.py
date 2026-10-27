"""Phase 1 recon: load saved session, open one problem, record every network
response while opening the Submissions tab, dump DOM + screenshot."""
import asyncio, json, pathlib, sys, re
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else \
    "https://neetcode.io/problems/unique-length-3-palindromic-subsequences/question"
OUT = pathlib.Path("recon"); OUT.mkdir(exist_ok=True)
HEADED = "--headed" in sys.argv

async def main():
    log = open(OUT / "network.jsonl", "w", encoding="utf-8")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not HEADED)
        ctx = await browser.new_context(storage_state="auth/neetcode_state.json",
                                        viewport={"width": 1400, "height": 900})
        page = await ctx.new_page()

        async def on_response(resp):
            try:
                ct = resp.headers.get("content-type", "")
                rec = {"url": resp.url, "status": resp.status, "ct": ct,
                       "method": resp.request.method}
                if resp.request.post_data:
                    rec["post"] = resp.request.post_data[:3000]
                if any(k in ct for k in ("json", "text/plain", "javascript")) and \
                   not re.search(r"\.(js|css|woff2?)(\?|$)", resp.url):
                    try:
                        body = await resp.text()
                        rec["len"] = len(body)
                        rec["body"] = body[:200000]
                    except Exception as e:
                        rec["body_err"] = str(e)
                log.write(json.dumps(rec) + "\n"); log.flush()
            except Exception as e:
                log.write(json.dumps({"err": str(e)}) + "\n")
        page.on("response", lambda r: asyncio.ensure_future(on_response(r)))

        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(6000)
        (OUT / "page_question.html").write_text(await page.content(), encoding="utf-8")
        await page.screenshot(path=str(OUT / "q.png"))
        # is the user signed in?
        txt = await page.inner_text("body")
        print("signed-in heuristics: 'Sign in' in body:", "Sign in" in txt or "Log in" in txt)
        # find anything that looks like a submissions tab
        cands = page.locator("text=/submissions/i")
        n = await cands.count(); print("elements matching /submissions/i:", n)
        for i in range(min(n, 10)):
            el = cands.nth(i)
            try:
                print(i, await el.evaluate("e => e.tagName + ' ' + (e.className||'') + ' | ' + e.innerText.slice(0,60)"))
            except Exception as e: print(i, "err", e)
        if n:
            await cands.first.click()
            await page.wait_for_timeout(8000)
        (OUT / "page_submissions.html").write_text(await page.content(), encoding="utf-8")
        await page.screenshot(path=str(OUT / "subs.png"), full_page=True)
        print("current url:", page.url)
        await browser.close()
    log.close()

asyncio.run(main())
