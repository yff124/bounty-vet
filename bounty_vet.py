#!/usr/bin/env python3
"""bounty-vet -- before you spend a weekend on a bounty repo, check whether it has ever paid anyone.

The problem this solves
-----------------------
2026-10-16: a GitHub search for `label:bounty state:open` returned a freshly created repo
offering "$90-$125" per issue, with 1,366 open bounties. It looked like the best lead in
weeks. Three cheap reads later it was dead:

  * 162 pull requests closed, **0 merged**, empty leaderboard, payout = "points -> cash at
    0.72 USD" decided by an unnamed admin, plus an issue soliciting USDT donations;
  * a second repo carried `/bounty $50` in the issue body and 151 forks -- it turned out
    to be a *self-declared* "sandbox fixture for testing an automated OSS bounty-solving
    workflow", still open after 4.5 months and 68 agent `/claim` comments;
  * a third was a real Apache-2.0 project with a 66% merge rate in the sample we took
    (76% exact on a later re-read), but its agent on-ramp document says, in its own words:
    "Only volunteer work is executable here; proposed credits/cash are not funded
    assignments."

Two of the three share a shape: **high fork count, near-zero stars** (127/12, 151/24).
Humans do not fork a repo they have not starred; automated agents do. It is a smell, not a
verdict -- the third board is not inverted at all and still pays nothing.

None of the three was detectable from the label, the README headline, or the offered
amount. Two of the three had to be read past the README to find the sentence that
decided it.

What it measures
----------------
  1. `merge_ratio = merged / closed` pull requests -- the only payout evidence that is
     public. A board that has never merged anything has never paid anyone, whatever its
     README says about amounts.
  2. `fork_star_inversion = forks > stars` -- automated attention, not human demand.
  3. `self_declared` -- multi-word phrases in the description, README, and money-answer
     documents that say, in the project's own words, that this is a drill or that there
     is no cash.

Why multi-word phrases only
---------------------------
A single-word scan was measured and rejected: `sandbox` matched
`getAttestation({ useSandbox: false })` in an ordinary SDK README -- a false positive on a
legitimate repo. Verdicts therefore require a phrase, and every hit is printed with the
sentence it sat in so it can be read in context.

What it deliberately does NOT do
--------------------------------
  * It does not decide whether a bounty is worth doing. It answers "has this board ever
    merged anything" and "does the board say, itself, that this is unpaid".
  * It does not follow links. Measured 2026-10-16: one board's own `AGENTS.md` is clean;
    the sentence that decides it ("only volunteer work, credits are not funded
    assignments") lives in an *external* agent packet linked from it. So PLAUSIBLE still
    means "read the agent packet by hand" for any board that hands agents a URL.
  * Zero closed PRs => UNKNOWN. That is not "unviable" and not "viable"; there is simply
    no evidence yet, and the tool refuses to guess -- a brand-new board looks exactly like
    a black hole on day one.

Failure modes fixed on 2026-10-16 (all three found on live data, none by unit test)
----------------------------------------------------------------------------------
  1. A *transport* failure used to read as "no closed PRs". `GET /pulls?state=closed
     &per_page=100` on one large repo returns 606 KB and needs more than 25 s, so
     `--max-time 25` cut the body mid-JSON; the parse failed, the empty list was
     swallowed, and a repo with 1,979 closed PRs was reported UNKNOWN ("no evidence").
     Now every read returns `(data, error)` and a failed fetch yields ERROR, never
     UNKNOWN.
  2. Live mode only read the README, though `classify()` already accepted extra text. So a
     board whose README says "BOUNTIES.md for paid issues" read as PLAUSIBLE while the
     deciding sentence -- "no cash allocated to pay contributors" -- sat in BOUNTIES.md.
     A fixed list of money-answer documents and agent on-ramp documents is now read, and
     every hit is labelled with the file it came from.
  3. Widening the scanned text widened the false positives: a contributing guide saying
     "implementation-level tests in the unit-test harness" flipped a live 808-PR board to
     SANDBOX. Ambiguous engineering phrases now require a board word in the same sentence;
     unambiguous ones ("not a real task", "practice repository") still stand alone.

Cost
----
Two `/search` counts give *exact* closed/merged totals in about 2 s per repo, replacing a
paginated walk that had not finished after 7 minutes on 4 repos. Measured: 6 repos in
91 s. `/search` is capped at 30 requests/minute, so a sweep wider than ~15 boards at once
should be split; the paginated walk is kept as a fallback and its result is flagged
`(sampled)`.

Requirements: Python 3.9+, `curl`, and an authenticated `gh` CLI for live mode.

Usage
-----
  python3 bounty_vet.py --repo owner/name [--repo owner/name ...]
  python3 bounty_vet.py --fixtures fixtures/boards.json
  python3 bounty_vet.py --repo owner/name --json
  python3 bounty_vet.py --selftest

Exit codes: 0 = ok, 1 = selftest failure, 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

# Multi-word phrases only -- see "Why multi-word phrases only" above.
# Split in two, because widening the scanned text widened the false-positive surface: a
# contributing guide saying "implementation-level tests in the unit-test harness" flipped
# a live board to SANDBOX. Ambiguous engineering words therefore only count next to a
# board word; unambiguous ones stand alone.
SANDBOX_PHRASES_STRICT = [
    "not a real task", "practice repository", "simulation only",
]
SANDBOX_PHRASES_CONTEXTUAL = [
    "sandbox fixture", "test fixture", "test harness", "for testing", "dry run",
]
STANDALONE_CONTEXT = [
    "bounty", "bounties", "reward", "payout", "paid", "task", "assignment",
    "contributor", "claim",
]
SANDBOX_PHRASES = SANDBOX_PHRASES_STRICT + SANDBOX_PHRASES_CONTEXTUAL
UNFUNDED_PHRASES = [
    "not funded", "volunteer work", "volunteer contribution", "unpaid",
    "no payment", "not a paid", "credits are not", "points are not",
    # --- added after reading three boards by hand that the list above missed ---
    # BOUNTIES.md: "no cash allocated to pay contributors" + "deferred ledger"
    #   + "Recognition is the primary reward; cash is possible but not promised."
    # README.md: "Zero bounty. Maximum rigor." / "pays nothing and promises nothing."
    "zero bounty", "zero bounties paid", "pays nothing", "pays nothing and promises nothing",
    "possible but not promised", "deferred ledger", "no cash allocated",
    "recognition is the primary reward",
]
CLOSED_PHRASES = [
    "not accepting", "paused", "closed to new", "on hold",
]

MIN_CLOSED_FOR_VERDICT = 5      # below this there is no evidence either way
BLACKHOLE_MIN_CLOSED = 20       # a real board merges *something* in 20 closed PRs
LOW_MERGE_RATIO = 0.20
PLAUSIBLE_RATIO = 0.50


def phrases_in(text: str, phrases, require_context=None) -> list:
    """Find multi-word phrases, returning each one with the sentence it sat in.

    `require_context`: when given, a hit is kept only if one of those words appears in
    the *same sentence*. This is what keeps "test harness" in an ordinary engineering
    README from being read as "this board is a drill".
    """
    low = (text or "").lower()
    out = []
    for p in phrases:
        i = low.find(p)
        if i < 0:
            continue
        start = max(0, low.rfind(".", 0, i) + 1)
        end = low.find(".", i)
        end = len(low) if end < 0 else end + 1
        sentence = re.sub(r"\s+", " ", text[start:end]).strip()
        if require_context and not any(w in sentence.lower() for w in require_context):
            continue
        out.append({"phrase": p, "context": sentence[:300]})
    return out


def classify(rec: dict) -> dict:
    repo = rec.get("repo") or {}
    counts = rec.get("counts") or {}
    if "closed" in counts:
        closed = int(counts.get("closed") or 0)
        merged = int(counts.get("merged") or 0)
        sampled = bool(counts.get("sampled"))
    else:                       # fixtures written before 2026-10-16 carry a PR list
        prs = rec.get("prs") or []
        closed = len(prs)
        merged = sum(1 for p in prs if p.get("merged_at"))
        sampled = False
    ratio = (merged / closed) if closed else 0.0
    stars = repo.get("stargazers_count") or 0
    forks = repo.get("forks_count") or 0

    # Tag every hit with the document it came from, so a verdict can be checked in one
    # hop instead of being re-derived by hand.
    sandbox, unfunded, closed_sig = [], [], []
    for doc, body in (("description", repo.get("description") or ""),
                      ("README", rec.get("readme") or ""),
                      ("extra", rec.get("extra_text") or "")):
        for h in phrases_in(body, SANDBOX_PHRASES_STRICT):
            h["doc"] = doc
            sandbox.append(h)
        for h in phrases_in(body, SANDBOX_PHRASES_CONTEXTUAL, STANDALONE_CONTEXT):
            h["doc"] = doc
            sandbox.append(h)
        for h in phrases_in(body, UNFUNDED_PHRASES):
            h["doc"] = doc
            unfunded.append(h)
        for h in phrases_in(body, CLOSED_PHRASES):
            h["doc"] = doc
            closed_sig.append(h)

    if rec.get("error"):
        # A fetch failure must never be read as "this board has no evidence".
        verdict, why = "ERROR", (f"fetch failed => do NOT read this as \"no evidence / "
                                 f"not viable\": {rec['error']} "
                                 f"({closed} closed PRs seen, for reference only)")
    elif sandbox:
        verdict, why = "SANDBOX", f"self-describes as a drill: \"{sandbox[0]['phrase']}\""
    elif unfunded:
        verdict, why = "UNFUNDED", f"self-describes as unfunded: \"{unfunded[0]['phrase']}\""
    elif closed >= BLACKHOLE_MIN_CLOSED and merged == 0:
        verdict, why = "BLACKHOLE", f"{closed} PRs closed, 0 merged => nobody has ever been accepted"
    elif closed < MIN_CLOSED_FOR_VERDICT:
        verdict, why = "UNKNOWN", f"only {closed} closed PRs => no evidence either way"
    elif ratio < LOW_MERGE_RATIO:
        verdict, why = "LOW_MERGE", f"merge ratio {ratio:.0%} ({merged}/{closed}) => the bar is probably not code quality"
    elif ratio >= PLAUSIBLE_RATIO:
        verdict, why = "PLAUSIBLE", f"merge ratio {ratio:.0%} ({merged}/{closed}) => it does merge things; worth reading by hand"
    else:
        verdict, why = "MIXED", f"merge ratio {ratio:.0%} ({merged}/{closed}) => half and half, needs a human call"

    return {
        "slug": rec.get("slug"),
        "verdict": verdict, "why": why,
        "closed_prs": closed, "merged_prs": merged, "merge_ratio": round(ratio, 3),
        "sampled": sampled,
        "stars": stars, "forks": forks,
        "fork_star_inversion": forks > stars,
        "size_kb": repo.get("size"),
        "closed_signal": [h["phrase"] for h in closed_sig],
        "evidence": [h["context"] for h in (sandbox + unfunded)[:2]],
        "evidence_doc": [h["doc"] for h in (sandbox + unfunded)[:2]],
        "extra_docs_read": rec.get("extra_docs") or [],
        "error": rec.get("error"),
    }


# ---------- live mode ----------

def _api(path: str, token: str, timeout: int = 60):
    """Return (data, err). err is a human-readable reason, or None on success.

    Why this returns a pair: the single-value version turned a *transport failure* into
    "the repo has no closed PRs", the worst possible failure mode for this tool -- it made
    a real board look like a brand-new one. Measured: `GET /pulls?state=closed&per_page=100`
    on a large repo returns 606 KB and takes more than 25 s, so `--max-time 25` cut it off
    mid-body; the truncated JSON failed to parse, the empty list was swallowed, and the
    verdict came out UNKNOWN ("no evidence") for a repo with 1,979 closed PRs.
    """
    import tempfile
    fd, tmp = tempfile.mkstemp()
    os.close(fd)
    try:
        r = subprocess.run(
            ["curl", "-sS", "--max-time", str(timeout), "-o", tmp, "-w", "%{http_code}",
             "-H", f"Authorization: token {token}",
             "-H", "Accept: application/vnd.github+json",
             f"https://api.github.com{path}"], capture_output=True, text=True)
        try:
            raw = open(tmp, encoding="utf-8", errors="replace").read()
        except OSError:
            raw = ""
        if r.returncode != 0:
            return None, f"curl exit {r.returncode} (timeout/aborted), {len(raw)} B received"
        try:
            return json.loads(raw), None
        except json.JSONDecodeError as e:
            return None, f"JSON parse failed ({len(raw)} B, looks truncated): {e.msg}"
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


# Root-level documents that carry the money answer far more often than the README does.
# Measured: one board's README only says "BOUNTIES.md for paid issues"; the sentence that
# actually decides it ("no cash allocated to pay contributors") lives in BOUNTIES.md.
# Missing documents 404 in ~100 ms, so probing the whole list is cheap.
EXTRA_DOCS = ["BOUNTIES.md", "CONTRIBUTING.md", "PROGRAM.md", "LEDGER.md",
              "GOVERNANCE.md", "CLA.md", "docs/bounties.md",
              # agent on-ramp documents: measured, one board's AGENTS.md (3,985 B) is where
              # an agent is told the terms, and it is not the README
              "AGENTS.md", "llms.txt", "llms-full.txt", "CLAUDE.md"]
EXTRA_DOC_MAX_BYTES = 400_000


def _search_count(slug: str, qualifier: str, token: str):
    """Exact `total_count` for e.g. `is:pr+is:merged`, in ~1 s and ~400 B.

    Why this exists: paginating `/pulls?state=closed` to reach the true totals costs
    8 requests x 600-790 KB on a large repo. Measured: a 4-repo run had not finished after
    7 minutes. Two search calls give the *exact* numbers instead of a bounded sample, for
    about 2 s per repo.
    """
    data, err = _api(f"/search/issues?q=repo:{slug}+{qualifier}&per_page=1", token)
    if err or not isinstance(data, dict) or "total_count" not in data:
        return None, err or "search_unreadable"
    return int(data["total_count"]), None


def fetch_live(slug: str, token: str) -> dict:
    import base64
    repo, err = _api(f"/repos/{slug}", token)
    if err or not repo or "full_name" not in repo:
        return {"slug": slug, "repo": {}, "prs": [], "error": err or "repo_unreadable"}

    errs = []
    closed, e1 = _search_count(slug, "is:pr+is:closed", token)
    merged, e2 = _search_count(slug, "is:pr+is:merged", token)
    sampled = False
    if closed is None or merged is None:
        errs.append(f"search counts unavailable (closed={e1} / merged={e2}) => "
                    f"falling back to the core API sample")
        got = _sample_prs(slug, token, errs)
        if got is None:
            return _err_record(slug, repo, errs)
        closed, merged, sampled = got[0], got[1], True

    readme = ""
    rm, rm_err = _api(f"/repos/{slug}/readme", token)
    if isinstance(rm, dict) and rm.get("content"):
        readme = base64.b64decode(rm["content"]).decode("utf-8", "replace")

    extras, found = [], []
    for doc in EXTRA_DOCS:
        d, de = _api(f"/repos/{slug}/contents/{doc}", token)
        if de or not isinstance(d, dict) or d.get("type") != "file":
            continue
        if (d.get("size") or 0) > EXTRA_DOC_MAX_BYTES or not d.get("content"):
            continue
        try:
            extras.append(f"===== {doc} =====\n"
                          + base64.b64decode(d["content"]).decode("utf-8", "replace"))
            found.append(doc)
        except Exception:
            continue

    out = {"slug": slug,
           "repo": {k: repo.get(k) for k in
                    ("full_name", "description", "size", "stargazers_count",
                     "forks_count", "open_issues_count")},
           "counts": {"closed": closed, "merged": merged, "sampled": sampled},
           "readme": readme, "extra_text": "\n".join(extras), "extra_docs": found}
    if errs:
        out["error"] = "; ".join(errs)
    return out


def _sample_prs(slug: str, token: str, errs: list):
    """Core-API fallback: bounded sample, small pages. Returns (closed, merged) or None."""
    prs, page, page_size = [], 1, 30
    while page <= 12:
        batch, e = _api(f"/repos/{slug}/pulls?state=closed&per_page={page_size}&page={page}",
                        token)
        if e:
            errs.append(f"pulls p{page}: {e}")
            return None
        prs += [{"merged_at": p.get("merged_at")} for p in batch]
        if len(batch) < page_size:
            break
        page += 1
    if not prs:
        return 0, 0
    return len(prs), sum(1 for p in prs if p.get("merged_at"))


def _err_record(slug: str, repo: dict, errs: list) -> dict:
    return {"slug": slug,
            "repo": {k: repo.get(k) for k in
                     ("full_name", "description", "size", "stargazers_count",
                      "forks_count", "open_issues_count")},
            "counts": {"closed": 0, "merged": 0, "sampled": True},
            "prs": [], "error": "; ".join(errs) or "fetch_failed"}


# ---------- selftest ----------

def _selftest() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    fx = os.path.join(here, "fixtures")
    boards = json.load(open(os.path.join(fx, "boards.json")))
    # Verbatim API reads, not retyped by hand (see fixtures/refetch.py, which wrote them).
    llms = open(os.path.join(fx, "llms_Uuriko_project-room.txt"), encoding="utf-8").read()
    mk_readme = open(os.path.join(fx, "readme_Ikalus1988_MisakaNet.txt"),
                     encoding="utf-8").read()
    oc_readme = open(os.path.join(fx, "readme_Element-Ventures-Canada-Ltd_openchokepoint.txt"),
                     encoding="utf-8").read()
    oc_bounties = open(os.path.join(fx, "bounties_Element-Ventures-Canada-Ltd_openchokepoint.md"),
                       encoding="utf-8").read()
    ophir_contrib = open(os.path.join(fx, "contributing_OphirPay_OphirPay.md"),
                         encoding="utf-8").read()

    def V(key, extra=None, base=None):
        rec = dict(base if base is not None else boards[key])
        if extra is not None:
            rec["extra_text"] = extra
        return classify(rec)["verdict"]

    cases = [
        # measured facts, 2026-10-16
        ("zhangjiayang6835-cyber_bounty-plaza", None, "BLACKHOLE"),   # 162 closed / 0 merged
        ("tine1117_oss-hunter-livefire", None, "SANDBOX"),            # 30 closed / 0 merged
        ("Uuriko_project-room", None, "PLAUSIBLE"),                   # 3068 closed / 2343 merged
        ("Uuriko_project-room", llms, "UNFUNDED"),                    # ...the on-ramp doc says so
        # synthetic guards
        ("_synth_lowmerge", None, "LOW_MERGE"),
        ("_synth_clean", None, "PLAUSIBLE"),
        ("_synth_brand_new", None, "UNKNOWN"),
    ]
    # A board created today looks exactly like a black hole. This case used to point at a
    # real repo whose fixture claimed "0 closed PRs" -- which turned out to be a silently
    # swallowed fetch failure written into the baseline, not a fact about the repo (its
    # first PR was closed 21 minutes after the repo was created). Kept synthetic on
    # purpose: the assertion is about the *rule*, and a real repo cannot be trusted to
    # still be new tomorrow.
    boards["_synth_brand_new"] = {
        "slug": "synth/brand-new",
        "repo": {"description": "bounties, $90-$125 per issue", "size": 120,
                 "stargazers_count": 2, "forks_count": 0},
        "counts": {"closed": 0, "merged": 0, "sampled": False},
        "readme": "# Bounties\nWe pay $90-$125 per issue.\n",
    }
    boards["_synth_lowmerge"] = {
        "slug": "synth/lowmerge",
        "repo": {"description": "bounties for our SDK", "size": 900, "stargazers_count": 400,
                 "forks_count": 50},
        "prs": [{"merged_at": "2026-01-01"} for _ in range(3)]
               + [{"merged_at": None} for _ in range(97)],
        "readme": "# Bounties\nWe pay for merged PRs.\n"
    }
    boards["_synth_clean"] = {
        "slug": "synth/clean",
        "repo": {"description": "paid bounty board", "size": 5000, "stargazers_count": 900,
                 "forks_count": 120},
        "prs": [{"merged_at": "2026-01-01"} for _ in range(66)]
               + [{"merged_at": None} for _ in range(34)],
        "readme": "# Bounties\nPaid on merge. See CONTRIBUTING.\n"
    }

    # --- regression set: three shapes the first version got wrong ---
    # Each record below carries the *measured* numbers and the *verbatim* text that the
    # live API returned for that repo, so the assertions sit on the phrase that decides it.
    boards["_real_MisakaNet"] = {
        "slug": "Ikalus1988/MisakaNet",
        "repo": {"description": "zero-dependency git-backed micro-lesson library",
                 "size": 48367, "stargazers_count": 526, "forks_count": 216},
        "prs": [{"merged_at": "2026-01-01"} for _ in range(1396)]
               + [{"merged_at": None} for _ in range(583)],
        "readme": mk_readme,
    }
    boards["_real_openchokepoint"] = {
        "slug": "Element-Ventures-Canada-Ltd/openchokepoint",
        "repo": {"description": "Open grammar for supply-chain dependency registries",
                 "size": 141, "stargazers_count": 0, "forks_count": 6},
        "prs": [{"merged_at": "2026-01-01"} for _ in range(13)]
               + [{"merged_at": None} for _ in range(4)],
        "readme": oc_readme,
    }
    cases += [
        # README alone misses it (it only says "BOUNTIES.md for paid issues") => PLAUSIBLE
        ("_real_openchokepoint", None, "PLAUSIBLE"),
        # ...the money answer is in BOUNTIES.md => UNFUNDED
        ("_real_openchokepoint", oc_bounties, "UNFUNDED"),
        # 76% merge rate on a real board, and it still pays nothing in cash
        ("_real_MisakaNet", None, "UNFUNDED"),
        # a failed fetch must never be reported as "no evidence"
        ("_err_case", None, "ERROR"),
    ]
    boards["_err_case"] = {
        "slug": "synth/fetch-timeout",
        "repo": {"description": "bounties", "size": 100, "stargazers_count": 10, "forks_count": 2},
        "prs": [],
        "error": "curl exit 28 (timeout/aborted), 606305 B received",
    }

    # --- SANDBOX false-positive regression ---
    # A real CONTRIBUTING.md contains "unit-test harness"; before the context gate that
    # flipped a live 808-PR board to SANDBOX. Verbatim file, measured counts.
    boards["_real_OphirPay"] = {
        "slug": "OphirPay/OphirPay",
        "repo": {"description": "Send, batch, schedule, and track blockchain payments",
                 "size": 35767, "stargazers_count": 5, "forks_count": 202},
        "counts": {"closed": 808, "merged": 222, "sampled": False},
        "readme": "# OphirPay\nSee CONTRIBUTING.md.\n",
    }
    # positive control for the gate: same phrase, but this sentence *is* about a board
    boards["_synth_gated_sandbox"] = {
        "slug": "synth/gated-sandbox",
        "repo": {"description": "A test harness for an automated bounty-solving workflow",
                 "size": 100, "stargazers_count": 3, "forks_count": 40},
        "counts": {"closed": 0, "merged": 0, "sampled": False},
        "readme": "# x\n",
    }
    cases += [
        ("_real_OphirPay", ophir_contrib, "MIXED"),
        ("_synth_gated_sandbox", None, "SANDBOX"),
    ]

    ok = 0
    for key, extra, want in cases:
        got = V(key, extra)
        flag = "OK " if got == want else "FAIL"
        if got == want:
            ok += 1
        print(f"  [{flag}] {key}{' +extra' if extra else ''}: want={want} got={got}")

    inversion = classify(boards["zhangjiayang6835-cyber_bounty-plaza"])["fork_star_inversion"]
    want_inv = True
    print(f"  [{'OK ' if inversion == want_inv else 'FAIL'}] "
          f"fork_star_inversion(bounty-plaza) want={want_inv} got={inversion}")
    ok += inversion == want_inv

    print(f"\nselftest {ok}/{len(cases) + 1}")
    return 0 if ok == len(cases) + 1 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", action="append", default=[],
                    help="owner/name to fetch live (repeatable)")
    ap.add_argument("--fixtures", help="a JSON file of records instead of live reads")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--selftest", action="store_true", help="offline, no network")
    a = ap.parse_args()

    if a.selftest:
        return _selftest()

    records = []
    if a.fixtures:
        data = json.load(open(a.fixtures))
        records = list(data.values()) if isinstance(data, dict) else data
    elif a.repo:
        token = subprocess.run(["gh", "auth", "token"], capture_output=True,
                               text=True).stdout.strip()
        if not token:
            print("no token from `gh auth token`; live mode needs an authenticated gh CLI",
                  file=sys.stderr)
            return 2
        records = [fetch_live(s, token) for s in a.repo]
    else:
        ap.error("need --repo or --fixtures")

    results = [classify(r) for r in records]
    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    for r in results:
        print(f"{r['verdict']:10s} {r['slug']}")
        print(f"           {r['why']}")
        print(f"           closed={r['closed_prs']} merged={r['merged_prs']} "
              f"{'(sampled)' if r['sampled'] else ''}"
              f"stars={r['stars']} forks={r['forks']} "
              f"inverted={r['fork_star_inversion']} size={r['size_kb']}KB")
        if r["closed_signal"]:
            print(f"           status words: {r['closed_signal']}")
        if r["extra_docs_read"]:
            print(f"           extra documents read: {r['extra_docs_read']}")
        for e, d in zip(r["evidence"], r["evidence_doc"]):
            print(f"           source [{d}]: {e}")
        if r["error"]:
            print(f"           fetch error: {r['error']}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
