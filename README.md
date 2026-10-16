# bounty-vet

**Before you spend a weekend on a bounty repo, find out whether it has ever paid anyone — in one command.**

On 2026-10-16 a GitHub search for `label:bounty state:open` returned a freshly created repo
offering **$90–$125 per issue** with **1,366 open bounties**. It was the best-looking lead in
weeks. Three cheap reads later it was dead:

| the pitch | what was actually there |
|---|---|
| a fresh board, 1,366 open bounties, $90–$125 each | **162 pull requests closed, 0 merged**, empty leaderboard, payout = "points → cash at 0.72 USD" decided by an unnamed admin, plus an issue soliciting USDT donations |
| `/bounty $50` in the issue body, 151 forks | a **self-declared** "sandbox fixture for testing an automated OSS bounty-solving workflow", still open after 4.5 months and 68 agent `/claim` comments |
| a real Apache-2.0 project, 66% merge rate | its own agent on-ramp doc: *"Only volunteer work is executable here; proposed credits/cash are not funded assignments."* |

None of the three was detectable from the label, the offered amount, or the README headline.
Two of the three needed a document *other than the README* to settle it.

`bounty-vet` gives each board a verdict on three signals that are cheap to read and hard to fake.

## Verdicts

| verdict | meaning |
|---|---|
| `BLACKHOLE` | 20+ pull requests closed, **0 merged** — nobody has ever been accepted, whatever the README promises |
| `SANDBOX` | the project says, in its own words, that this is a drill or a test fixture |
| `UNFUNDED` | the project says, in its own words, that there is no cash |
| `LOW_MERGE` | merge ratio under 20% — the bar is probably not code quality |
| `MIXED` | 20–50% — a human needs to look |
| `PLAUSIBLE` | 50%+ merged, and nothing self-declared against it; worth reading by hand |
| `UNKNOWN` | fewer than 5 closed PRs — **no evidence either way**, not "no" and not "yes" |
| `ERROR` | a read failed. **Never** reported as "no evidence" — see below |

## Real output

```
$ python3 bounty_vet.py --repo zhangjiayang6835-cyber/bounty-plaza \
                        --repo Element-Ventures-Canada-Ltd/openchokepoint \
                        --repo parabola-org/parabola

BLACKHOLE  zhangjiayang6835-cyber/bounty-plaza
           162 PRs closed, 0 merged => nobody has ever been accepted
           closed=162 merged=0 stars=12 forks=127 inverted=True size=132KB

UNFUNDED   Element-Ventures-Canada-Ltd/openchokepoint
           self-describes as unfunded: "unpaid"
           closed=17 merged=13 stars=0 forks=6 inverted=True size=141KB
           extra documents read: ['BOUNTIES.md', 'CONTRIBUTING.md', 'PROGRAM.md', 'LEDGER.md', 'GOVERNANCE.md', 'CLA.md']
           source [extra]: - **Sunset:** entries still unpaid on 31 March 2028 become recognition-only and are marked **Lapsed**.
           source [extra]: No payment is made in advance of accepted work.

MIXED      parabola-org/parabola
           merge ratio 30% (30/101) => half and half, needs a human call
           closed=101 merged=30 stars=1 forks=32 inverted=True size=430KB
```

Read the second one carefully: its **README says "BOUNTIES.md for paid issues"**. The
sentence that decides it — *"no cash allocated to pay contributors"*, *"cash is possible
but not promised"*, a **deferred ledger** — is in `BOUNTIES.md`. A README-only check calls
that board clean.

## How each signal is read

**Merge ratio** — `merged / closed`, from two `/search` calls, exact rather than sampled.
A board that has never merged anything has never paid anyone. This is the only payout
evidence that is public.

**Fork/star inversion** (`forks > stars`) — humans do not fork a repo they have not
starred; automated agents do. Measured on the boards above: 127 forks / 12 stars,
151 forks / 24 stars. It is a smell, not a verdict — one of the boards in the fixtures has
a *non*-inverted ratio and still pays nothing.

**Self-declared text** — the description, the README, and a fixed list of money-answer and
agent on-ramp documents (`BOUNTIES.md`, `CONTRIBUTING.md`, `PROGRAM.md`, `LEDGER.md`,
`GOVERNANCE.md`, `CLA.md`, `AGENTS.md`, `llms.txt`, `llms-full.txt`, `CLAUDE.md`, …).
Missing documents 404 in ~100 ms, so probing the whole list is cheap. Every hit is printed
with the sentence it sat in, and with the file it came from.

## What it deliberately does not do

- **It does not decide whether a bounty is worth doing.** It answers two narrow questions:
  has this board ever merged anything, and does the board itself say this is unpaid.
- **It does not follow links.** One measured board's own `AGENTS.md` is clean; the sentence
  that decides it lives in an *external* agent packet linked from it. So `PLAUSIBLE` still
  means "read the agent packet by hand" for any board that hands agents a URL.
- **It does not guess.** Zero closed PRs is `UNKNOWN`. A board created today looks exactly
  like a black hole, and the tool refuses to invent a difference that does not exist yet.
- **It never writes.** Read-only core API; it does not comment, label, claim, or fork.

## Usage

```bash
python3 bounty_vet.py --repo owner/name [--repo owner/name ...]   # live
python3 bounty_vet.py --repo owner/name --json                    # machine-readable
python3 bounty_vet.py --fixtures fixtures/boards.json             # offline replay
python3 bounty_vet.py --selftest                                  # offline, no network
```

- **Python 3.9+**, standard library only — no install step.
- Needs `curl` and an authenticated [`gh` CLI](https://cli.github.com) for live mode (it
  shells out to `gh auth token`; it never stores credentials itself).
- Measured cost: **6 repos in 91 s**. `/search` is capped at 30 requests/minute, so split a
  sweep wider than ~15 boards; a paginated walk is kept as a fallback and its result is
  flagged `(sampled)`.

## Tests

```
$ python3 bounty_vet.py --selftest
  [OK ] zhangjiayang6835-cyber_bounty-plaza: want=BLACKHOLE got=BLACKHOLE
  ...
  [OK ] _synth_brand_new: want=UNKNOWN got=UNKNOWN

selftest 14/14
```

Fixtures are **verbatim API reads**, never retyped — a paraphrased fixture makes a test
green for the wrong reason. `fixtures/README.md` documents where each one came from, and
why one of them had to be deleted.

## Three failure modes, all found on live data, none by the tests

1. **A transport failure read as "no data".** `GET /pulls?state=closed&per_page=100` returns
   606 KB on a large repo and can need more than 25 s. `curl --max-time 25` cut the body
   mid-JSON, the parse failed, **the empty list was swallowed**, and a repo with 1,979 closed
   pull requests was reported `UNKNOWN` — "no evidence". Every read now returns
   `(data, error)`, and a failed fetch yields `ERROR`, never `UNKNOWN`.
   This one then went one step further: it wrote the corrupted result into the **fixture
   file**, so the regression baseline itself asserted a false fact. Details in
   `fixtures/README.md`.
2. **Reading only the README.** Live mode now reads the money-answer and agent on-ramp
   documents and labels every hit with its source file. That single change flipped one board
   from `PLAUSIBLE` to `UNFUNDED`.
3. **Widening the scan created false positives.** A contributing guide mentioning
   "implementation-level tests in the unit-test harness" flipped a live 808-PR board to
   `SANDBOX`. Ambiguous engineering phrases now only count when a board word ("bounty",
   "payout", "claim", …) appears **in the same sentence**; unambiguous ones ("not a real
   task", "practice repository") still stand alone.

## Why this exists

`label:bounty` no longer means "there is money here". Measured across the boards above, it
now covers at least three different things: foundation-funded work, zero-cash ledger and
credits experiments, and black boxes that accept nothing. All three are indistinguishable
from a paid board until you read past the headline — and the checks were being done by hand,
inconsistently, once per session.

MIT.

---

Footnote, so the output above is not read as a claim of virtue: this tool was written by
someone who was hunting these boards. Four of the boards named in this README are ones it
was *about to* spend time on. It reports the state of the board, not what anyone hoped it
was.
