import asyncio, json, pathlib, re
from playwright.async_api import async_playwright
OUT = pathlib.Path("recon")
async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(storage_state="auth/neetcode_state.json")
        page = await ctx.new_page()
        hdrs = {}
        async def on_req(req):
            if "getProblemMetadata" in req.url or "callableFunctionHttp" in req.url:
                hdrs[req.url + "|" + (req.post_data or "")[:80]] = {k: (v[:40] + "...") if k.lower() == "authorization" else v for k, v in req.headers.items()}
        page.on("request", lambda r: asyncio.ensure_future(on_req(r)))
        practice_log = []
        async def on_resp(resp):
            ct = resp.headers.get("content-type", "")
            if "json" in ct and not re.search(r"\.(js|css)(\?|$)", resp.url):
                try: body = await resp.text()
                except Exception: body = ""
                practice_log.append({"url": resp.url, "post": resp.request.post_data, "len": len(body), "body": body})
        page.on("response", lambda r: asyncio.ensure_future(on_resp(r)))
        await page.goto("https://neetcode.io/practice?tab=allNC", wait_until="domcontentloaded")
        await page.wait_for_timeout(8000)
        print("--- request headers seen ---")
        for k, v in hdrs.items(): print(k, "\n   ", {h: v[h] for h in v if h.lower() in ("authorization", "content-type", "x-firebase-appcheck", "cookie")})
        print("--- practice page json responses ---")
        for r in practice_log: print(r["len"], r["url"][:120], (r["post"] or "")[:100])
        json.dump(practice_log, open(OUT / "practice_network.json", "w", encoding="utf-8"))
        # token from IndexedDB
        tok = await page.evaluate("""() => new Promise(res => {
            const req = indexedDB.open('firebaseLocalStorageDb');
            req.onsuccess = e => { const db = e.target.result;
              const tx = db.transaction('firebaseLocalStorage','readonly');
              const g = tx.objectStore('firebaseLocalStorage').getAll();
              g.onsuccess = () => { const v = g.result[0] && g.result[0].value; res(v ? {uid: v.uid, exp: v.stsTokenManager.expirationTime, tok: v.stsTokenManager.accessToken} : null); };
            }; req.onerror = () => res(null); })""")
        print("idb token present:", bool(tok), "exp:", tok and tok["exp"])
        # direct API call from page context for another problem
        r = await page.evaluate("""async (tok) => {
            const r = await fetch('/api/getProblemMetadataFunctionHttp', {method:'POST',
              headers:{'content-type':'application/json','authorization':'Bearer '+tok},
              body: JSON.stringify({data:{problemId:'two-integer-sum'}})});
            const j = await r.json(); const d = j.data || {};
            return {status: r.status, name: d.name, completed: d.completed, n: (d.submissionHistory||[]).length,
                    first: (d.submissionHistory||[]).map(s => [s.statusDescription, s.date, s.language])};
        }""", tok["tok"])
        print("direct fetch two-integer-sum:", json.dumps(r))
        r2 = await page.evaluate("""async (tok) => {
            const r = await fetch('/api/getProblemMetadataFunctionHttp', {method:'POST',
              headers:{'content-type':'application/json'},
              body: JSON.stringify({data:{problemId:'two-integer-sum'}})});
            const j = await r.json(); const d = j.data || {};
            return {status: r.status, hasHistory: 'submissionHistory' in d, n: (d.submissionHistory||[]).length};
        }""", tok["tok"])
        print("direct fetch WITHOUT auth:", json.dumps(r2))
        await browser.close()
asyncio.run(main())
