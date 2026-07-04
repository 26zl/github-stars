#!/usr/bin/env python3
# Group starred repos into README.md by their GitHub topics, falling back to language.
import csv, collections, datetime, os, sys

SRC = "starred.tsv"
OUT = "README.md"

# whose stars: set by update.sh / GitHub Actions, else the logged-in gh user
OWNER = (os.environ.get("OWNER") or os.environ.get("GITHUB_REPOSITORY_OWNER")
         or os.popen("gh api user --jq .login 2>/dev/null").read().strip()).lower()
if not OWNER:
    print("note: owner unresolved (set OWNER or run 'gh auth login'); 'My repos' skipped", file=sys.stderr)

MIN_TOPIC = 5             # a topic needs this many repos to become a category (else fall back to language)
MIN_SHOW = 3              # categories smaller than this fold into "Other"
IGNORE = {"hacktoberfest"}  # participation tag, not a topic

def esc(s):  # escape markdown/HTML in untrusted descriptions
    for ch in "[]<`*":
        s = s.replace(ch, "\\" + ch)
    return s
def norm(s):  # display label for a topic or language
    return s.replace("-", " ").title()

rows = []
with open(SRC) as f:
    for i, r in enumerate(csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE), 1):  # some descs start with a literal "
        if len(r) != 5:  # gh @tsv always emits 5 fields
            raise SystemExit(f"{SRC} line {i}: expected 5 tab-separated fields, got {len(r)}")
        name, lang, stars, topics, desc = r[0], r[1], int(r[2] or 0), r[3], r[4]
        topics = [t for t in topics.split(",") if t and t not in IGNORE]
        rows.append((name, lang, stars, topics, desc))

freq = collections.Counter(t for _, _, _, topics, _ in rows for t in topics)  # how common each topic is

def category(name, lang, topics):
    if name.split("/", 1)[0].lower() == OWNER:
        return "My repos"
    popular = [t for t in topics if freq[t] >= MIN_TOPIC]
    if popular:
        return norm(max(sorted(popular), key=lambda t: freq[t]))  # most common; ties -> alphabetical, stable
    return norm(lang) if lang else "Other"

buckets = collections.defaultdict(list)
for name, lang, stars, topics, desc in rows:
    buckets[category(name, lang, topics)].append((name, lang, stars, desc))

# fold small categories into language, else Other
for c in [c for c, items in list(buckets.items()) if len(items) < MIN_SHOW and c not in ("My repos", "Other")]:
    for row in buckets.pop(c):
        buckets[norm(row[1]) if row[1] else "Other"].append(row)
for c in [c for c, items in list(buckets.items()) if len(items) < MIN_SHOW and c not in ("My repos", "Other")]:
    buckets["Other"].extend(buckets.pop(c))

def human(n): return f"{n:,}"
order = sorted(buckets, key=lambda c: (c == "Other", c != "My repos", -len(buckets[c]), c))

with open(OUT, "w") as o:
    o.write("# ⭐ My GitHub Stars\n\n")
    o.write(f"Auto-generated from my **{len(rows)}** starred repos, grouped by their GitHub topics "
            f"and sorted by stars within each. ")
    o.write(f"Last updated {datetime.date.fromtimestamp(os.path.getmtime(SRC)).isoformat()} · "
            f"auto-refreshed weekly · `./update.sh` to refresh manually.\n\n")
    o.write("> Fork this repo and enable GitHub Actions to build your own — the workflow indexes "
            "whoever owns the repo, no setup needed. Locally: `gh auth login`, then `./update.sh`.\n\n")
    o.write("## Contents\n\n")
    for c in order:
        o.write(f"- {c} ({len(buckets[c])})\n")
    o.write("\n")
    for c in order:
        items = sorted(buckets[c], key=lambda x: -x[2])
        o.write(f"## {c} ({len(items)})\n\n")
        for name, lang, stars, desc in items:
            lg = f" `{lang}`" if lang else ""
            d = f" — {esc(desc)}" if desc else ""
            o.write(f"- **[{name}](https://github.com/{name})** ⭐{human(stars)}{lg}{d}\n")
        o.write("\n")

print(f"{len(rows)} repos -> {len(order)} categories, Other={len(buckets['Other'])}")
