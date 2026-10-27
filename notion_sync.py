"""Sync Claude-written tips into the Notion "Neetcode" database via the official API.

Setup:
  1. Create an internal integration at https://www.notion.so/profile/integrations
     (capabilities: read content, update content, insert content).
  2. Share the Neetcode database with it (database page -> ... -> Connections -> add the integration).
  3. Put the token in .env:   NOTION_TOKEN=ntn_xxx        (.env is gitignored)

Commands:
  uv run python notion_sync.py check              # token works, database reachable, lists properties
  uv run python notion_sync.py dump-rows          # -> data/notion_rows_full.json (all rows + notes)
  uv run python notion_sync.py ensure-property    # create the "claude tips" rich_text property if missing
  uv run python notion_sync.py plan               # show what write-tips would do (no writes)
  uv run python notion_sync.py write-tips [--create-missing] [--dup newest|all] [--only slug ...]

Input: out/tips.json  {slug: "tip text"}  (written by the tip-generation step).
Only the "claude tips" property is ever overwritten; existing rows' other properties are untouched,
except an empty URL on a row listed in ALIASES, which is filled in (so duplicates aren't created).
"""
import argparse, json, pathlib, re, sys, time
import httpx
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.environ.get("NOTION_TOKEN")
DS_ID = "3e454c1b-345a-8014-b859-000b6fecbab7"
PROP = "claude tips"
API = "https://api.notion.com/v1"
HDR = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2025-09-03", "Content-Type": "application/json"}
TIPS = pathlib.Path("out/tips.json")
SUBS = pathlib.Path("out/submissions.jsonl")
ROWS_FULL = pathlib.Path("data/notion_rows_full.json")

# NeetCode slug -> existing Notion row that lacks a URL but is the same problem
ALIASES = {
    "task-scheduling": "3e454c1b345a8062abf5efd9daa0113b",            # "Task Scheduler"
    "maximum-sum-circular-subarray": "3e854c1b345a80acadeffe406408648e",  # "Maximum Sum Circular Subarray"
}

client = httpx.Client(timeout=60)


def req(method, path, **kw):
    for attempt in range(5):
        r = client.request(method, API + path, headers=HDR, **kw)
        if r.status_code == 429 or r.status_code >= 500:
            wait = float(r.headers.get("Retry-After", 2 ** attempt))
            print(f"  {r.status_code} on {path}, retrying in {wait}s"); time.sleep(wait); continue
        if r.status_code >= 400:
            raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:500]}")
        time.sleep(0.35)  # ~3 req/s limit
        return r.json()
    raise RuntimeError(f"gave up on {path}")


def slug_of(url):
    m = re.search(r"/problems/([^/?#]+)", url or "")
    return m.group(1) if m else None


def norm(name):
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def plain(rt):
    return "".join(t.get("plain_text", "") for t in rt or [])


def page_id_of(url_or_id):
    return re.sub(r"-", "", url_or_id.rstrip("/").split("/")[-1].split("?")[0])[-32:]


def rich_text(text, limit=2000):
    chunks = [text[i:i + limit] for i in range(0, len(text), limit)] or [""]
    return [{"type": "text", "text": {"content": c}} for c in chunks]


def get_schema():
    return req("GET", f"/data_sources/{DS_ID}")["properties"]


def fetch_rows():
    rows, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor: body["start_cursor"] = cursor
        res = req("POST", f"/data_sources/{DS_ID}/query", json=body)
        for p in res["results"]:
            pr = p["properties"]
            rows.append({
                "id": p["id"].replace("-", ""), "created": p["created_time"],
                "name": plain(pr["Name"]["title"]), "url": pr["URL"]["url"],
                "level": (pr["My Level of Understanding"]["select"] or {}).get("name"),
                "difficulty": (pr["Problem Level"]["select"] or {}).get("name"),
                "intuition": plain(pr["My intuition"]["rich_text"]),
                "missed": plain(pr["What I missed"]["rich_text"]),
                "refresher": plain(pr["Bullet Points Refresher"]["rich_text"]),
                "tips": plain(pr[PROP]["rich_text"]) if PROP in pr else None,
            })
        if not res.get("has_more"): break
        cursor = res["next_cursor"]
    return rows


def load_problems():
    probs = {}
    for line in open(SUBS, encoding="utf-8"):
        p = json.loads(line); probs[p["slug"]] = p
    return probs


def match_rows(rows):
    """slug -> list of rows (newest first)."""
    by_slug, by_name = {}, {}
    for r in rows:
        s = slug_of(r["url"])
        if s: by_slug.setdefault(s, []).append(r)
        by_name.setdefault(norm(r["name"]), []).append(r)
    for slug, pid in ALIASES.items():
        for r in rows:
            if r["id"] == pid and slug not in by_slug:
                by_slug[slug] = [r]
    for s in by_slug: by_slug[s].sort(key=lambda r: r["created"], reverse=True)
    return by_slug, by_name


def build_plan(args):
    tips = json.load(open(TIPS, encoding="utf-8"))
    probs = load_problems()
    rows = fetch_rows()
    by_slug, by_name = match_rows(rows)
    plan = {"update": [], "create": [], "fill_url": [], "unmatched": []}
    for slug, text in tips.items():
        if args.only and slug not in args.only: continue
        prob = probs.get(slug, {})
        targets = by_slug.get(slug) or by_name.get(norm(prob.get("name"))) or []
        if not targets:
            plan["unmatched"].append(slug); continue
        chosen = targets if args.dup == "all" else targets[:1]
        for r in chosen:
            plan["update"].append((slug, r, text))
            if not r["url"] and slug in ALIASES:
                plan["fill_url"].append((slug, r))
    for slug in plan["unmatched"]:
        p = probs[slug]
        plan["create"].append((slug, p["name"], p["url"], p.get("difficulty"), tips[slug]))
    return plan


def main():
    global PROP, TIPS
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "dump-rows", "ensure-property", "plan", "write-tips", "show"])
    ap.add_argument("--create-missing", action="store_true")
    ap.add_argument("--dup", choices=["newest", "all"], default="newest")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("slugs", nargs="*", help="positional slugs (same as --only), e.g. `show two-integer-sum`")
    ap.add_argument("--prop", default=PROP, help='target rich_text property (default "claude tips")')
    ap.add_argument("--tips", default=str(TIPS), help="JSON {slug: text} to write (default out/tips.json)")
    args = ap.parse_args()
    args.only = (args.only or []) + (args.slugs or []) or None
    PROP, TIPS = args.prop, pathlib.Path(args.tips)
    if not TOKEN:
        sys.exit("NOTION_TOKEN missing. Put NOTION_TOKEN=ntn_... in .env")

    if args.cmd == "check":
        me = req("GET", "/users/me"); print("integration:", me.get("name"), me.get("type"))
        schema = get_schema()
        print("database reachable; properties:", sorted(schema))
        print(f'"{PROP}" exists:', PROP in schema)
        return

    if args.cmd == "show":
        # one problem: the user's Notion notes, current tip, and a submission summary from the local backup
        rows = fetch_rows(); by_slug, by_name = match_rows(rows)
        probs = load_problems() if SUBS.exists() else {}
        for slug in args.only or []:
            p = probs.get(slug, {})
            print(f"=== {p.get('name', slug)}  ({slug}, {p.get('difficulty')})  {p.get('url', '')}")
            for r in by_slug.get(slug) or by_name.get(norm(p.get("name"))) or []:
                print(f"[Notion row {r['id']} created {r['created'][:10]} | understanding: {r['level']}]")
                print(f"  My intuition: {r['intuition'] or '(empty)'}")
                print(f"  What I missed: {r['missed'] or '(empty)'}")
                print(f"  Bullet Points Refresher: {r['refresher'] or '(empty)'}")
                print(f"  claude tips: {r['tips'] or '(empty)'}")
            subs = p.get("submissions", [])
            print(f"submissions: {len(subs)}  " + ", ".join(f"{s['status_raw']} ({s['tests_passed']}/{s['tests_total']})" for s in subs))
            print(f"code + failing cases: out/{slug}.md")
        return

    if args.cmd == "dump-rows":
        rows = fetch_rows(); ROWS_FULL.parent.mkdir(exist_ok=True)
        json.dump(rows, open(ROWS_FULL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"{len(rows)} rows -> {ROWS_FULL}"); return

    if args.cmd == "ensure-property":
        schema = get_schema()
        if PROP in schema:
            print(f'"{PROP}" already exists ({schema[PROP]["type"]})'); return
        req("PATCH", f"/data_sources/{DS_ID}", json={"properties": {PROP: {"rich_text": {}}}})
        print(f'created rich_text property "{PROP}"'); return

    plan = build_plan(args)
    print(f"rows to update: {len(plan['update'])}   rows to create: {len(plan['create'])}   "
          f"URLs to fill: {len(plan['fill_url'])}")
    for slug, r in plan["fill_url"]: print(f"  fill URL on '{r['name']}' <- {slug}")
    for slug, name, url, diff, _ in plan["create"]: print(f"  create row: {name} [{diff}] {url}")
    if args.cmd == "plan":
        for slug, r, text in plan["update"][:5]:
            print(f"  e.g. {r['name']} ({slug}): {len(text)} chars")
        return

    schema = get_schema()
    if PROP not in schema:
        sys.exit(f'property "{PROP}" missing; run ensure-property first')
    n = 0
    for slug, r, text in plan["update"]:
        props = {PROP: {"rich_text": rich_text(text)}}
        if any(x[1]["id"] == r["id"] for x in plan["fill_url"]):
            props["URL"] = {"url": f"https://neetcode.io/problems/{slug}/question"}
        req("PATCH", f"/pages/{r['id']}", json={"properties": props})
        n += 1; print(f"  updated {r['name']} ({slug})")
    c = 0
    if plan["create"]:
        if not args.create_missing:
            print(f"{len(plan['create'])} problems have no row; re-run with --create-missing to create them")
        else:
            for slug, name, url, diff, text in plan["create"]:
                props = {"Name": {"title": rich_text(name)}, "URL": {"url": url}, PROP: {"rich_text": rich_text(text)}}
                if diff in ("Easy", "Medium", "Hard"): props["Problem Level"] = {"select": {"name": diff}}
                req("POST", "/pages", json={"parent": {"type": "data_source_id", "data_source_id": DS_ID}, "properties": props})
                c += 1; print(f"  created {name} ({slug})")
    print(f"\ndone: {n} rows updated, {c} rows created, {len(plan['unmatched']) - c} unmatched left")


if __name__ == "__main__":
    main()
