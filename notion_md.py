"""Render out/submissions.jsonl into Notion-flavored Markdown sections, one file per problem,
plus a manifest mapping each Notion row to its section file.

Section shape (idempotency marker = the toggle heading text prefix "Submissions (auto-imported"):

<toggle heading="h2">
Submissions (auto-imported YYYY-MM-DD)

...children...
</toggle>

Usage: uv run python notion_md.py [--date YYYY-MM-DD]
"""
import argparse, datetime as dt, json, pathlib, re

OUT = pathlib.Path("out"); DEST = OUT / "notion"; DEST.mkdir(exist_ok=True)
MARK = "Submissions (auto-imported"

def fence_for(code):
    longest = max((len(m) for m in re.findall(r"`+", code)), default=0)
    return "`" * max(3, longest + 1)

def esc(s):
    return str(s).replace("<", "\\<").replace("\n", " ")

def render(prob, date):
    subs = prob["submissions"]
    acc = sum(1 for s in subs if s["status"] == "accepted")
    lines = ['<toggle heading="h2">', f"{MARK} {date})", "",
             f"{len(subs)} submissions, {acc} accepted. Source: [{prob['slug']}]({prob['url']}). "
             f"Imported {prob['scraped_at'][:10]} by `scrape.py`.", ""]
    for i, s in enumerate(subs, 1):
        ts = s["timestamp"].replace("T", " ")[:16] + " UTC"
        icon = "✅" if s["status"] == "accepted" else "❌"
        tests = f" · tests {s['tests_passed']}/{s['tests_total']}" if s.get("tests_passed") is not None else ""
        lines.append(f"### {icon} {i}. {s['status_raw']} — {ts}{tests}")
        lines.append("")
        fc = s.get("failing_test_case")
        if fc and s["status"] != "accepted":
            lines.append(f"Failing case: input `{esc(fc.get('input',''))}` → expected `{esc(fc.get('expected_output',''))}`, got `{esc(fc.get('user_output','') or '∅')}`")
            lines.append("")
        if s.get("stderr", "").strip():
            f = fence_for(s["stderr"])
            lines += [f + "text", s["stderr"].strip()[:1500], f, ""]
        f = fence_for(s["code"])
        lines += [f + s["language"], s["code"].rstrip(), f, ""]
    while lines and lines[-1] == "":
        lines.pop()
    lines.append("</toggle>")
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default=dt.date.today().isoformat())
    a = ap.parse_args()
    manifest = []
    for line in open(OUT / "submissions.jsonl", encoding="utf-8"):
        p = json.loads(line)
        if not p["submissions"]:
            continue
        md = render(p, a.date)
        path = DEST / f"{p['slug']}.notion.md"
        path.write_text(md, encoding="utf-8")
        for row in p["notion_rows"]:
            manifest.append({"slug": p["slug"], "notion_url": row["notion_url"], "name": row["name"],
                             "file": str(path), "n_subs": len(p["submissions"]), "chars": len(md)})
        if not p["notion_rows"]:
            manifest.append({"slug": p["slug"], "notion_url": None, "name": p["name"], "file": str(path),
                             "n_subs": len(p["submissions"]), "chars": len(md)})
    json.dump(manifest, open(DEST / "manifest.json", "w", encoding="utf-8"), indent=1)
    rows = [m for m in manifest if m["notion_url"]]
    print(f"sections: {len(set(m['slug'] for m in manifest))}  notion rows to update: {len(rows)}  "
          f"unmatched problems: {sum(1 for m in manifest if not m['notion_url'])}")
    print(f"total chars for notion rows: {sum(m['chars'] for m in rows):,}  largest: "
          f"{max(rows, key=lambda m: m['chars'])['slug']} {max(m['chars'] for m in rows):,}")

if __name__ == "__main__":
    main()
