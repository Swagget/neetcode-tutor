"""Phase 4 verification: Notion tips vs out/tips.json, backup vs live NeetCode, idempotency."""
import json, random, re, subprocess, sys
subprocess.run([sys.executable, "notion_sync.py", "dump-rows"], check=True, capture_output=True)
rows = json.load(open("data/notion_rows_full.json", encoding="utf-8"))
tips = json.load(open("out/tips.json", encoding="utf-8"))
probs = {json.loads(l)["slug"]: json.loads(l) for l in open("out/submissions.jsonl", encoding="utf-8")}
def slug_of(u):
    m = re.search(r"/problems/([^/?#]+)", u or ""); return m.group(1) if m else None
by_slug = {}
for r in rows:
    s = slug_of(r["url"])
    if s: by_slug.setdefault(s, []).append(r)
for s in by_slug: by_slug[s].sort(key=lambda r: r["created"], reverse=True)
ok = mismatch = 0; missing = []
for slug, text in tips.items():
    rs = by_slug.get(slug)
    if not rs: missing.append(slug); continue
    if (rs[0]["tips"] or "").strip() == text.strip(): ok += 1
    else: mismatch += 1; print("MISMATCH", slug, len(rs[0]["tips"] or ""), len(text))
with_tips = sum(1 for r in rows if r["tips"])
print(f"notion rows total: {len(rows)}   rows with claude tips: {with_tips}")
print(f"tips matching source exactly: {ok}/{len(tips)}   mismatches: {mismatch}   problems with no row: {missing}")
no_tips = [r["name"] for r in rows if not r["tips"]]
print(f"rows without tips ({len(no_tips)}): {no_tips}")
dups = {s: [r['name'] for r in rs] for s, rs in by_slug.items() if len(rs) > 1}
print("duplicate-row problems (tips on newest only):", {s: [bool(r['tips']) for r in by_slug[s]] for s in dups})
# live spot-check: 3 random problems re-fetched from NeetCode
random.seed()
sample = random.sample([s for s in tips if probs[s]["submissions"]], 3)
before = {s: [(x["status_raw"], x["timestamp"], len(x["code"])) for x in probs[s]["submissions"]] for s in sample}
subprocess.run([sys.executable, "scrape.py", "--slugs", *sample], check=True, capture_output=True)
after_probs = {json.loads(l)["slug"]: json.loads(l) for l in open("out/submissions.jsonl", encoding="utf-8")}
for s in sample:
    after = [(x["status_raw"], x["timestamp"], len(x["code"])) for x in after_probs[s]["submissions"]]
    print(f"spot-check {s}: backup {len(before[s])} subs, live {len(after)} subs, identical={before[s]==after}; "
          f"notion row '{by_slug[s][0]['name']}' tips {len(by_slug[s][0]['tips'])} chars, "
          f"starts: {by_slug[s][0]['tips'][:70]!r}")
