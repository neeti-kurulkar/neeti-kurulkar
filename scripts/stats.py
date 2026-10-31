"""Render stats.svg for the profile README from the GitHub GraphQL API.

Runs in GitHub Actions (see .github/workflows/stats.yml) with GITHUB_TOKEN.
Standard library only. Pass --demo to render with made-up numbers, for
checking the layout locally without a token.
"""
import json
import os
import sys
import urllib.request
from html import escape

USER = os.environ.get("STATS_USER", "neeti-kurulkar")
OUT = os.path.join(os.path.dirname(__file__), "..", "stats.svg")

QUERY = """
query($login: String!) {
  user(login: $login) {
    pullRequests { totalCount }
    issues { totalCount }
    contributionsCollection { totalCommitContributions restrictedContributionsCount }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

# languages that are mostly generated or bulky, and would drown the real ones
SKIP_LANGS = {"Jupyter Notebook", "HTML", "CSS", "SCSS", "Procfile", "Dockerfile", "Makefile", "Batchfile", "PowerShell", "Shell"}


def fetch():
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        sys.exit(f"GraphQL error: {body['errors']}")
    u = body["data"]["user"]
    langs = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            n = e["node"]["name"]
            if n in SKIP_LANGS:
                continue
            c = e["node"]["color"] or "#7d8796"
            langs.setdefault(n, [0, c])[0] += e["size"]
    cc = u["contributionsCollection"]
    return {
        "stars": sum(r["stargazerCount"] for r in u["repositories"]["nodes"]),
        "commits": cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
        "prs": u["pullRequests"]["totalCount"],
        "issues": u["issues"]["totalCount"],
        "repos": u["repositories"]["totalCount"],
        "langs": sorted(((n, s, c) for n, (s, c) in langs.items()), key=lambda x: -x[1])[:5],
    }


def demo():
    return {
        "stars": 12, "commits": 342, "prs": 18, "issues": 7, "repos": 31,
        "langs": [("Python", 60, "#3572A5"), ("JavaScript", 25, "#f1e05a"),
                  ("TypeScript", 8, "#3178c6"), ("Java", 4, "#b07219"), ("C++", 3, "#f34b7d")],
    }


def render(d):
    W, H = 495, 195
    bg, line, head, text, muted = "#0b0e13", "#1d242e", "#6fa6e0", "#e9eef4", "#7d8796"
    font = "font-family=\"'Segoe UI', Ubuntu, -apple-system, Helvetica, Arial, sans-serif\""
    rows = [("Total stars", d["stars"]), ("Commits (past year)", d["commits"]),
            ("Pull requests", d["prs"]), ("Issues", d["issues"]), ("Repositories", d["repos"])]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub stats for {USER}">',
           f'<rect width="{W}" height="{H}" rx="4.5" fill="{bg}"/>']
    # left: the numbers
    y = 48
    for label, val in rows:
        out.append(f'<text x="28" y="{y}" {font} font-size="13" fill="{muted}">{escape(label)}</text>')
        out.append(f'<text x="222" y="{y}" {font} font-size="14" font-weight="700" fill="{text}" text-anchor="end">{val:,}</text>')
        y += 29
    out.append(f'<line x1="247" y1="28" x2="247" y2="{H-28}" stroke="{line}"/>')
    # right: top languages
    out.append(f'<text x="272" y="48" {font} font-size="13" font-weight="700" fill="{head}">Top languages</text>')
    total = sum(s for _, s, _ in d["langs"]) or 1
    x, bar_w = 272, 196
    for _, s, c in d["langs"]:
        w = bar_w * s / total
        out.append(f'<rect x="{x:.1f}" y="60" width="{w:.1f}" height="8" fill="{c}"/>')
        x += w
    y = 92
    for n, s, c in d["langs"]:
        out.append(f'<circle cx="277" cy="{y-4}" r="4" fill="{c}"/>')
        out.append(f'<text x="288" y="{y}" {font} font-size="12" fill="{text}">{escape(n)}</text>')
        out.append(f'<text x="468" y="{y}" {font} font-size="12" fill="{muted}" text-anchor="end">{100*s/total:.0f}%</text>')
        y += 20
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    data = demo() if "--demo" in sys.argv else fetch()
    with open(OUT, "w") as f:
        f.write(render(data) + "\n")
    print("wrote", os.path.abspath(OUT))
