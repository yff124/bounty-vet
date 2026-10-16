# fixtures

Every file here is a **verbatim API read**, not something retyped by hand. The selftest
asserts on these strings, so a paraphrase would make the test green for the wrong reason.

| file | what it is | captured |
|---|---|---|
| `boards.json` | repo + counts + README for three boards, plus an exact `counts` block per board | 2026-10-16, counts re-read 2026-10-17 |
| `readme_Ikalus1988_MisakaNet.txt` | README of a board with a 70% merge rate that pays nothing | 2026-10-16 |
| `readme_Element-Ventures-Canada-Ltd_openchokepoint.txt` | the README that *looks* fine | 2026-10-16 |
| `bounties_Element-Ventures-Canada-Ltd_openchokepoint.md` | the document that actually decides it | 2026-10-16 |
| `contributing_OphirPay_OphirPay.md` | a false-positive control: contains "unit-test harness" | 2026-10-16 |
| `llms_Uuriko_project-room.txt` | an agent on-ramp document, reached from the repo but not part of it | 2026-10-16 |
| `refetch.py` | regenerates `boards.json` through the tool's own fetcher | — |

## One fixture had to be deleted, and the reason is worth a paragraph

`boards.json` originally carried a fourth board -- `parabola-org/parabola` -- recorded as
having **0 closed pull requests**, and the selftest used it as the real-world example of
the "no evidence yet => UNKNOWN" rule.

It was wrong, and not because the API lied:

* the repo was created `2026-10-15T20:00:31Z`;
* its **first pull request was closed at `2026-10-15T20:21:49Z`**, 21 minutes later;
* when the fixture was written on 2026-10-16 it already had dozens of closed PRs.

What actually happened is the failure mode the tool had *just* been fixed for: the
fixture-writing fetcher used `--max-time 25` on `GET /pulls?state=closed&per_page=100`,
which on a large repo returns 606 KB and can need more than 25 s. The body was cut
mid-JSON, the parse failed, **the failure was swallowed, and an empty list was written to
disk as a measurement**. The bug did not merely produce one wrong verdict -- it poisoned
the regression baseline, where it would have gone on asserting a false fact indefinitely.

Re-running that same fetcher today returns 101 closed / 30 merged, so the failure is
**transient and not reproducible on demand**; the only reason it was caught is that this
repo is small enough to date every pull request. The record was removed, and that case
was replaced with a **synthetic** brand-new board -- the rule being tested is about the
rule, not about one repo, and a real repo cannot be trusted to still be new tomorrow.
