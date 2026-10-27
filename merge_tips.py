"""Validate out/tips/<slug>.txt (3-line tutor format) and merge them into out/tips.json for notion_sync.py.

Format (exactly 3 lines, <=45 words total, <=12 words after each label):
  🔑 Key idea: ...
  ⚠️ My trap: ...
  ❓ Next time ask: ...
Exit code 1 if any file is invalid (so the sync is not run on bad tips).
"""
import json, pathlib, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows console can't print the emoji labels otherwise
T = pathlib.Path("out/tips")
LABELS = ["🔑 Key idea:", "⚠️ My trap:", "❓ Next time ask:"]
SPEAK_LABEL = "🗣️ Say it:"          # optional 4th line, only when a recording was used
MAX_WORDS_LINE, MAX_WORDS_TOTAL, MAX_WORDS_WITH_SPEAK = 12, 45, 57


def words(s):
    return len(re.findall(r"\S+", s))


def validate(txt):
    lines = [l.strip() for l in txt.strip().replace("\r\n", "\n").split("\n") if l.strip()]
    errs = []
    if len(lines) not in (3, 4):
        return [f"expected 3 lines (4 with {SPEAK_LABEL}), got {len(lines)}"]
    labels = LABELS + ([SPEAK_LABEL] if len(lines) == 4 else [])
    max_total = MAX_WORDS_WITH_SPEAK if len(lines) == 4 else MAX_WORDS_TOTAL
    total = 0
    for line, label in zip(lines, labels):
        if not line.startswith(label):
            errs.append(f"line must start with {label!r}: {line[:40]!r}"); continue
        body = line[len(label):].strip()
        if not body: errs.append(f"{label} is empty")
        n = words(body); total += n
        if n > MAX_WORDS_LINE: errs.append(f"{label} has {n} words (max {MAX_WORDS_LINE})")
        if re.search(r"attempt|submission \d|subs? \d", body, re.I): errs.append(f"{label} narrates history")
        if "`" in body or "**" in body: errs.append(f"{label} has markdown")
    if total > max_total: errs.append(f"{total} words total (max {max_total})")
    return errs


def main():
    probs = {json.loads(l)["slug"] for l in open("out/submissions.jsonl", encoding="utf-8")}
    check = "--check" in sys.argv  # validate only, never write tips.json
    only = set(a for a in sys.argv[1:] if a != "--check")
    tips, bad = {}, 0
    for f in sorted(T.glob("*.txt")):
        slug = f.stem
        if only and slug not in only: continue
        txt = f.read_text(encoding="utf-8-sig").strip().replace("\r\n", "\n")
        if slug not in probs: print(f"  WARN {slug}: not a scraped problem"); continue
        errs = validate(txt)
        if errs:
            bad += 1; print(f"  INVALID {slug}: " + "; ".join(errs)); continue
        tips[slug] = "\n".join(l.strip() for l in txt.split("\n") if l.strip())
    if check:
        print(f"checked {len(tips) + bad} tip(s), invalid: {bad}")
        sys.exit(1 if bad else 0)
    if not only:
        missing = sorted(probs - set(tips))
        json.dump(tips, open("out/tips.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"tips: {len(tips)}  invalid: {bad}  no tip: {len(missing)} {missing[:8]}")
    else:
        existing = json.load(open("out/tips.json", encoding="utf-8")) if pathlib.Path("out/tips.json").exists() else {}
        existing.update(tips)
        json.dump(existing, open("out/tips.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"validated {len(tips)} tip(s), invalid: {bad}; out/tips.json now has {len(existing)}")
    if tips:
        w = sorted(words(t) for t in tips.values()); print(f"words min/median/max: {w[0]}/{w[len(w)//2]}/{w[-1]}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
