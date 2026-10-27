"""Bundle each problem's submissions + the user's Notion notes into out/tipwork/<slug>.md
and split slugs into N groups for parallel tip writing."""
import json, pathlib, re, sys
N = int(sys.argv[1]) if len(sys.argv) > 1 else 6
OUT = pathlib.Path("out"); W = OUT / "tipwork"; W.mkdir(exist_ok=True); (OUT / "tips").mkdir(exist_ok=True)
rows = json.load(open("data/notion_rows_full.json", encoding="utf-8"))
ALIASES = {"task-scheduling": "3e454c1b345a8062abf5efd9daa0113b", "maximum-sum-circular-subarray": "3e854c1b345a80acadeffe406408648e"}
def slug_of(u):
    m = re.search(r"/problems/([^/?#]+)", u or ""); return m.group(1) if m else None
notes = {}
for r in rows:
    s = slug_of(r["url"]) or next((k for k, v in ALIASES.items() if v == r["id"]), None)
    if s: notes.setdefault(s, []).append(r)
probs = [json.loads(l) for l in open(OUT / "submissions.jsonl", encoding="utf-8")]
slugs = []
for p in probs:
    if not p["submissions"]: continue
    L = [f"# {p['name']}  (slug: {p['slug']}, {p['difficulty']})", ""]
    for r in sorted(notes.get(p["slug"], []), key=lambda r: r["created"]):
        L += [f"## User's own Notion notes (row created {r['created'][:10]}, understanding: {r['level']})",
              f"- My intuition: {r['intuition'] or '(empty)'}", f"- What I missed: {r['missed'] or '(empty)'}",
              f"- Bullet Points Refresher: {r['refresher'] or '(empty)'}", ""]
    if not notes.get(p["slug"]): L += ["## User's own Notion notes: none (no row yet)", ""]
    L += [f"## Submissions ({len(p['submissions'])} total, chronological)", ""]
    for i, s in enumerate(p["submissions"], 1):
        L.append(f"### {i}. {s['status_raw']} — {s['timestamp'][:16]} — tests {s['tests_passed']}/{s['tests_total']}")
        fc = s.get("failing_test_case")
        if fc and s["status"] != "accepted":
            L.append(f"failing case: input={fc.get('input')!r} expected={fc.get('expected_output')!r} got={fc.get('user_output')!r}")
        if s.get("stderr", "").strip(): L += ["stderr:", "```", s["stderr"].strip()[:1200], "```"]
        L += [f"```{s['language']}", s["code"].rstrip(), "```", ""]
    (W / f"{p['slug']}.md").write_text("\n".join(L), encoding="utf-8")
    slugs.append(p["slug"])
slugs.sort(key=lambda s: -sum(len(x["code"]) for x in next(p for p in probs if p["slug"] == s)["submissions"]))
groups = [[] for _ in range(N)]
for i, s in enumerate(slugs): groups[i % N].append(s)   # round-robin by size for balance
for i, g in enumerate(groups, 1):
    (W / f"group_{i}.txt").write_text("\n".join(g), encoding="utf-8")
    print(f"group_{i}: {len(g)} problems, {sum((W / f'{s}.md').stat().st_size for s in g)//1024} KB")
print("bundles:", len(slugs))
# new rows since the initial snapshot
old = {r["notion"].split("/")[-1] for r in json.load(open("data/notion_rows.json", encoding="utf-8"))}
for r in rows:
    if r["id"] not in old: print("NEW ROW:", r["name"], r["url"], r["created"])
