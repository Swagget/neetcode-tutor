"""Back up NeetCode submission history (read-only).

Usage:
  uv run python scrape.py                 # all problems (Notion URLs + NeetCode completed list)
  uv run python scrape.py --since 2026-10-01   # keep only submissions on/after this date
  uv run python scrape.py --slugs two-integer-sum eating-bananas
  uv run python scrape.py --all-neetcode  # also probe every NeetCode slug (~1400 calls) to catch
                                          # attempted-but-never-accepted problems missing from Notion

Requires auth/neetcode_state.json from login.py. Never submits or modifies anything on NeetCode.
Outputs: out/submissions.jsonl (one problem per line), out/<slug>.md, out/failures.json
"""
import argparse, asyncio, datetime as dt, json, pathlib, random, re, sys, time
from playwright.async_api import async_playwright

STATE = pathlib.Path("auth/neetcode_state.json")
OUT = pathlib.Path("out")
NOTION_ROWS = pathlib.Path("data/notion_rows.json")
BASE = "https://neetcode.io"

GET_TOKEN_JS = """() => new Promise(res => {
  let req; try { req = indexedDB.open('firebaseLocalStorageDb'); } catch (e) { return res(null); }
  req.onerror = () => res(null);
  req.onsuccess = e => { const db = e.target.result;
    if (!db.objectStoreNames.contains('firebaseLocalStorage')) return res(null);
    const g = db.transaction('firebaseLocalStorage','readonly').objectStore('firebaseLocalStorage').getAll();
    g.onsuccess = () => { const v = g.result[0] && g.result[0].value;
      res(v ? {token: v.stsTokenManager.accessToken, exp: v.stsTokenManager.expirationTime, uid: v.uid} : null); };
    g.onerror = () => res(null); };
})"""

FETCH_JS = """async ([path, token, body]) => {
  const r = await fetch(path, {method: 'POST',
    headers: {'content-type': 'application/json', 'authorization': 'Bearer ' + token},
    body: JSON.stringify({data: body})});
  const text = await r.text();
  return {status: r.status, text};
}"""


class AuthExpired(Exception):
    pass


class Client:
    def __init__(self, page, concurrency):
        self.page = page
        self.sem = asyncio.Semaphore(concurrency)
        self.token = None
        self.exp = 0
        self.lock = asyncio.Lock()

    async def refresh_token(self, force_reload=False):
        async with self.lock:
            if not force_reload and self.token and self.exp - time.time() * 1000 > 120_000:
                return self.token
            if force_reload:
                await self.page.reload(wait_until="domcontentloaded")
                await self.page.wait_for_timeout(3000)
            for _ in range(10):
                info = await self.page.evaluate(GET_TOKEN_JS)
                if info and info["exp"] - time.time() * 1000 > 120_000:
                    self.token, self.exp = info["token"], info["exp"]
                    return self.token
                await asyncio.sleep(1)
            raise AuthExpired("No valid Firebase token in the session. Re-run login.py.")

    async def call(self, path, body, tries=3):
        last = None
        for attempt in range(tries):
            tok = await self.refresh_token()
            async with self.sem:
                try:
                    r = await self.page.evaluate(FETCH_JS, [path, tok, body])
                except Exception as e:
                    last = f"evaluate error: {e}"
                    r = None
            if r is not None:
                if r["status"] in (401, 403):
                    # token rejected: force a reload so the Firebase SDK refreshes it, then retry
                    await self.refresh_token(force_reload=True)
                    last = f"HTTP {r['status']}"
                elif r["status"] == 200:
                    try:
                        return json.loads(r["text"])
                    except Exception as e:
                        last = f"bad json: {e}"
                else:
                    last = f"HTTP {r['status']}: {r['text'][:200]}"
            await asyncio.sleep(1.5 * 2 ** attempt + random.random())
        raise RuntimeError(last or "unknown failure")


def slug_of(url):
    m = re.search(r"/problems/([^/?#]+)", url or "")
    return m.group(1) if m else None


def norm_status(s):
    s = (s or "").lower()
    if "accept" in s: return "accepted"
    if "wrong" in s: return "wrong answer"
    if "time limit" in s or "tle" in s: return "time limit exceeded"
    if "runtime" in s or "nzec" in s: return "runtime error"
    if "compil" in s: return "compile error"
    if "memory" in s: return "memory limit exceeded"
    return s or "unknown"


def to_md(prob):
    lines = [f"# {prob['name']}", "",
             f"- URL: {prob['url']}", f"- Difficulty: {prob.get('difficulty')}",
             f"- Submissions: {len(prob['submissions'])} "
             f"({sum(1 for s in prob['submissions'] if s['status'] == 'accepted')} accepted)", ""]
    for i, s in enumerate(prob["submissions"], 1):
        lines.append(f"## {i}. {s['status_raw']} — {s['timestamp']} ({s['language']})")
        meta = []
        if s.get("tests_passed") is not None:
            meta.append(f"tests {s['tests_passed']}/{s['tests_total']}")
        if s.get("runtime"): meta.append(f"runtime {s['runtime']}s")
        if s.get("memory"): meta.append(f"memory {s['memory']} KB")
        if meta: lines.append("- " + ", ".join(meta))
        fc = s.get("failing_test_case")
        if fc:
            lines.append("- Failing test case:")
            lines.append("  - input: `" + fc.get("input", "").replace("\n", " ") + "`")
            lines.append("  - expected: `" + str(fc.get("expected_output", "")).replace("\n", " ") + "`")
            lines.append("  - got: `" + str(fc.get("user_output", "")).replace("\n", " ") + "`")
        if s.get("stderr"):
            lines += ["- stderr:", "```", s["stderr"].strip()[:2000], "```"]
        lines += ["", f"```{s['language']}", s["code"].rstrip(), "```", ""]
    return "\n".join(lines)


def parse_submission(raw):
    fc = raw.get("last_executed_test_case")
    return {
        "timestamp": raw.get("date"),
        "status": norm_status(raw.get("statusDescription")),
        "status_raw": raw.get("statusDescription"),
        "language": raw.get("language"),
        "code": raw.get("code", ""),
        "runtime": raw.get("time"),
        "memory": raw.get("memory"),
        "tests_passed": raw.get("correct_test_case_count"),
        "tests_total": raw.get("test_case_count"),
        "failing_test_case": {k: fc.get(k) for k in ("input", "expected_output", "user_output", "test_case_index")} if fc else None,
        "stdout": raw.get("stdout") or "",
        "stderr": raw.get("stderr") or "",
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="ISO date; keep only submissions on/after it (problems with none are skipped)")
    ap.add_argument("--slugs", nargs="*", help="only these problem slugs")
    ap.add_argument("--all-neetcode", action="store_true", help="probe every NeetCode slug, not just Notion + completed")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
    since = dt.datetime.fromisoformat(args.since).replace(tzinfo=dt.timezone.utc) if args.since else None

    if not STATE.exists():
        sys.exit("auth/neetcode_state.json missing. Run: uv run python login.py")
    OUT.mkdir(exist_ok=True)

    notion_rows = json.load(open(NOTION_ROWS, encoding="utf-8")) if NOTION_ROWS.exists() else []
    notion_by_slug = {}
    for r in notion_rows:
        s = slug_of(r.get("url"))
        if s:
            notion_by_slug.setdefault(s, []).append({"notion_url": r["notion"], "name": r["name"], "url": r["url"]})

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not args.headed)
        ctx = await browser.new_context(storage_state=str(STATE))
        page = await ctx.new_page()
        await page.goto(BASE + "/", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        client = Client(page, args.concurrency)

        # --- auth canary ---
        try:
            await client.refresh_token()
        except AuthExpired as e:
            sys.exit(f"SESSION EXPIRED: {e}")
        info = await client.call("/api/callableFunctionHttp", {"functionId": "getUserInfo"})
        if not isinstance(info.get("data"), dict) or not info["data"]:
            sys.exit("SESSION EXPIRED: getUserInfo returned no user. Re-run login.py to re-authenticate.")
        print("authenticated as uid", (await page.evaluate(GET_TOKEN_JS))["uid"])

        # --- problem list ---
        plist = (await client.call("/api/getProblemListFunctionHttp", {"filter": "allNC"}))["data"]
        completed = {k for k, v in plist.items() if v.get("completed")}
        if args.slugs:
            from slug_from_url import slugs_from_args  # accepts NeetCode/LeetCode URLs or bare slugs
            slugs = slugs_from_args(args.slugs)
        elif args.all_neetcode:
            slugs = sorted(set(plist) | set(notion_by_slug))
        else:
            slugs = sorted(set(notion_by_slug) | completed)
        print(f"problems to scrape: {len(slugs)}  (notion {len(notion_by_slug)}, neetcode-completed {len(completed)})")

        results, failures, expired = {}, {}, False

        async def one(slug):
            nonlocal expired
            if expired: return
            try:
                resp = await client.call("/api/getProblemMetadataFunctionHttp", {"problemId": slug})
            except AuthExpired:
                expired = True; return
            except Exception as e:
                failures[slug] = str(e); print(f"  FAIL {slug}: {e}"); return
            d = resp.get("data") or {}
            if not d:
                failures[slug] = f"empty response: {json.dumps(resp)[:200]}"; return
            if "submissionHistory" not in d and "completed" not in d and slug in completed:
                # authenticated response always carries these for a completed problem
                expired = True; return
            subs = [parse_submission(s) for s in d.get("submissionHistory") or []]
            subs.sort(key=lambda s: s["timestamp"] or "")
            if since:
                subs = [s for s in subs if s["timestamp"] and dt.datetime.fromisoformat(s["timestamp"].replace("Z", "+00:00")) >= since]
            results[slug] = {
                "slug": slug, "name": d.get("name"), "url": f"{BASE}/problems/{slug}/question",
                "difficulty": d.get("difficulty"), "completed": bool(d.get("completed")),
                "notion_rows": notion_by_slug.get(slug, []),
                "submissions": subs, "scraped_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            }

        t0 = time.time()
        tasks = [asyncio.create_task(one(s)) for s in slugs]
        done = 0
        for t in asyncio.as_completed(tasks):
            await t; done += 1
            if done % 20 == 0: print(f"  {done}/{len(slugs)} done")
        await browser.close()

    if expired:
        sys.exit("SESSION EXPIRED mid-run: NeetCode stopped returning submission history. "
                 "Re-run `uv run python login.py` to re-authenticate, then re-run scrape.py.")

    # --- write outputs ---
    # Partial runs (--slugs / --since) merge into the existing backup instead of replacing it.
    jsonl = OUT / "submissions.jsonl"
    merged = {}
    if (args.slugs or since) and jsonl.exists():
        for line in open(jsonl, encoding="utf-8"):
            p = json.loads(line); merged[p["slug"]] = p
    written = 0
    for slug in sorted(results):
        prob = results[slug]
        if since and not prob["submissions"]:
            continue
        if since and slug in merged:
            # keep previously stored submissions, add the new ones by timestamp
            seen = {s["timestamp"] for s in merged[slug]["submissions"]}
            prob = dict(prob, submissions=sorted(
                merged[slug]["submissions"] + [s for s in prob["submissions"] if s["timestamp"] not in seen],
                key=lambda s: s["timestamp"] or ""))
        merged[slug] = prob
        (OUT / f"{slug}.md").write_text(to_md(prob), encoding="utf-8")
        written += 1
    with open(jsonl, "w", encoding="utf-8") as f:
        for slug in sorted(merged):
            f.write(json.dumps(merged[slug], ensure_ascii=False) + "\n")
    json.dump(failures, open(OUT / "failures.json", "w", encoding="utf-8"), indent=1)

    n_subs = sum(len(p["submissions"]) for p in results.values())
    with_subs = sum(1 for p in results.values() if p["submissions"])
    no_subs = sorted(s for s, p in results.items() if not p["submissions"])
    not_in_notion = sorted(s for s, p in results.items() if p["submissions"] and not p["notion_rows"])
    print("\n=== SUMMARY ===")
    print(f"problems queried:        {len(slugs)}  in {time.time() - t0:.1f}s")
    print(f"problems with subs:      {with_subs}")
    print(f"problems with no subs:   {len(no_subs)}  {no_subs[:20]}")
    print(f"submissions scraped:     {n_subs}")
    print(f"  accepted / other:      {sum(1 for p in results.values() for s in p['submissions'] if s['status']=='accepted')} / "
          f"{sum(1 for p in results.values() for s in p['submissions'] if s['status']!='accepted')}")
    print(f"files written:           {written} .md updated; submissions.jsonl now has {len(merged)} problems")
    print(f"failures after 3 tries:  {len(failures)}  {list(failures)[:20]}")
    print(f"have subs, no Notion row:{len(not_in_notion)}  {not_in_notion}")


if __name__ == "__main__":
    asyncio.run(main())
