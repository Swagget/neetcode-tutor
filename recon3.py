import asyncio, json
from playwright.async_api import async_playwright
GET_TOK = """() => new Promise(res => { const req = indexedDB.open('firebaseLocalStorageDb');
  req.onsuccess = e => { const db = e.target.result; const g = db.transaction('firebaseLocalStorage','readonly').objectStore('firebaseLocalStorage').getAll();
  g.onsuccess = () => res(g.result[0] && g.result[0].value.stsTokenManager.accessToken); }; req.onerror = () => res(null); })"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(storage_state="auth/neetcode_state.json")
        page = await ctx.new_page(); await page.goto("https://neetcode.io/", wait_until="domcontentloaded"); await page.wait_for_timeout(3000)
        tok = await page.evaluate(GET_TOK)
        for flt in ["allNC", "neetcode150", "neetcode250", "blind75", "neetcodeAll", "all"]:
            r = await page.evaluate("""async ([tok, flt]) => {
                const r = await fetch('/api/getProblemListFunctionHttp', {method:'POST', headers:{'content-type':'application/json','authorization':'Bearer '+tok}, body: JSON.stringify({data:{filter: flt}})});
                const t = await r.text(); let d; try { d = JSON.parse(t).data } catch(e) { return {status:r.status, raw:t.slice(0,200)} }
                const keys = Object.keys(d||{}); const k0 = keys[0];
                return {status:r.status, n: keys.length, sample_key: k0, sample: d && d[k0]};
            }""", [tok, flt])
            print(flt, json.dumps(r)[:600])
        json.dump(await page.evaluate("""async (tok) => { const r = await fetch('/api/getProblemListFunctionHttp', {method:'POST', headers:{'content-type':'application/json','authorization':'Bearer '+tok}, body: JSON.stringify({data:{filter:'allNC'}})}); return (await r.json()).data; }""", tok),
                  open("recon/problemlist_allNC.json", "w", encoding="utf-8"))
        await b.close()
asyncio.run(main())
