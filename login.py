"""Open a headed browser on neetcode.io, wait for the user to sign in manually,
then save the session (cookies + localStorage + IndexedDB, which is where Firebase
Auth keeps its token) to auth/neetcode_state.json.

Login is auto-detected by polling the Firebase IndexedDB store. As a fallback,
create the file auth/GO to force a save. Nothing is typed on the user's behalf.
"""
import asyncio, pathlib, sys, time
from playwright.async_api import async_playwright

STATE = pathlib.Path("auth/neetcode_state.json")
GO = pathlib.Path("auth/GO")
TIMEOUT_S = 15 * 60

FIREBASE_USER_COUNT = """
() => new Promise((res) => {
  let req;
  try { req = indexedDB.open('firebaseLocalStorageDb'); } catch (e) { return res(-1); }
  req.onupgradeneeded = (e) => { try { e.target.transaction.abort(); } catch (_) {} res(0); };
  req.onerror = () => res(-1);
  req.onsuccess = (e) => {
    const db = e.target.result;
    if (!db.objectStoreNames.contains('firebaseLocalStorage')) { db.close(); return res(0); }
    const tx = db.transaction('firebaseLocalStorage', 'readonly');
    const c = tx.objectStore('firebaseLocalStorage').count();
    c.onsuccess = () => { db.close(); res(c.result); };
    c.onerror = () => { db.close(); res(-1); };
  };
})
"""

async def main():
    STATE.parent.mkdir(exist_ok=True)
    GO.unlink(missing_ok=True)
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=False, channel="chrome",
                                              args=["--disable-blink-features=AutomationControlled"])
            print("using installed Google Chrome")
        except Exception as e:
            print("chrome channel unavailable, using bundled chromium:", e)
            browser = await p.chromium.launch(headless=False,
                                              args=["--disable-blink-features=AutomationControlled"])
        ctx = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await ctx.new_page()
        await page.goto("https://neetcode.io/", wait_until="domcontentloaded")
        print("Browser open. Please sign in to NeetCode in that window.")
        print("Auto-detecting login... (fallback: create file auth/GO)", flush=True)
        t0 = time.time()
        while time.time() - t0 < TIMEOUT_S:
            await asyncio.sleep(2)
            if GO.exists():
                print("GO file found."); break
            try:
                n = await page.evaluate(FIREBASE_USER_COUNT)
            except Exception:
                n = -1
            if n and n > 0:
                print(f"Firebase auth entry detected ({n}). Waiting 5s for cookies to settle...")
                await asyncio.sleep(5)
                break
        else:
            print("Timed out waiting for login."); await browser.close(); sys.exit(1)
        await ctx.storage_state(path=str(STATE), indexed_db=True)
        print(f"Saved session to {STATE} ({STATE.stat().st_size} bytes)")
        await browser.close()

asyncio.run(main())
