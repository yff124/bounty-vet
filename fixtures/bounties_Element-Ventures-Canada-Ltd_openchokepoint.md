Handling: Unclassified — public

> **STATUS: FINAL — approved by counsel, October 2026.**

# Bounties and the Deferred Ledger

EV does not currently have cash allocated to pay contributors. Bounties are
therefore recorded in a public **deferred ledger** (LEDGER.md) and paid only
from funds that arrive for that purpose. Recognition is the primary reward;
cash is possible but not promised.

## 1. How it works

1. Maintainers publish scoped issues labelled `bounty` and a tier label, each
   with acceptance tests and a nominal value in Canadian dollars.
2. A contributor comments to claim an issue. The first accepted pull request
   that meets the acceptance tests earns the entry. Maintainers may split a
   bounty between contributors where work was shared.
3. When the pull request is merged, a maintainer adds an **Accrued** entry to
   LEDGER.md in the same pull request.
4. Entries move to **Paid** only when funds are available (section 4).

Work merged before an issue carried a bounty label does not qualify.

### Proposals and dependencies

- A contributor may propose a scoped piece of work by comment before a bounty
  issue exists. A proposal reserves nothing and starts no obligation on either
  side. Do not begin work on the strength of a proposal alone.
- A proposal, suggestion, or other feedback earns no reward on its own. Only
  accepted work on a published bounty issue earns a ledger entry. Credit for
  feedback is covered by FEEDBACK.md.
- If maintainers accept a proposal in principle, they publish it as a bounty
  issue that names what it **depends on** (for example, a schema version that
  must be merged first).
- A bounty issue with an unmet dependency is labelled `blocked` and cannot be
  claimed. When the dependency merges, the label is removed and the proposer has
  14 days of first claim before the issue opens to anyone.
- Bounties that touch different files may be open at the same time.

### AI-assisted work

Work produced with AI assistance is eligible when all of the following hold:

1. The pull request states that AI Assistance was used and for which parts.
2. A Responsible Person (CLA.md section 11) has reviewed and approved the work
   and has accepted the CLA, or the Responsible Person's organization has signed
   the CCLA and listed them. An AI system cannot accept the CLA.
3. The ledger entry is made to the Responsible Person, not to an AI system or
   agent account.

Maintainers may ask for more detail on how AI Assistance was used and may
decline work whose originality they cannot establish.

### Verification before payment

Before any payment, maintainers confirm the identity of the human recipient and
that the CLA is accepted. No payment is made in advance of accepted work.

## 2. Tiers (nominal values, CAD)

| Tier | Typical work | Nominal value |
| :-- | :-- | :-- |
| `bounty:starter` | Documentation, tests, data-quality fixes | C$100 |
| `bounty:standard` | Connector, parser, schema extension | C$500 |
| `bounty:major` | Module, benchmark component, validated public-source dataset | C$1,500 |
| `bounty:expert` | Domain model review, adversarial review report | C$3,000 to C$5,000 |

## 3. Limits

- **Pool ceiling:** C$30,000 in total across all accrued entries.
- **Per-contributor ceiling:** C$5,000.
- EV will not accrue entries beyond the ceiling. Once the ceiling is reached,
  further work is recognised but earns no ledger value, unless the ceiling is
  raised by a published change to this document.

## 4. Funding Events and payment

Bounties are funded retroactively: work is recorded now and paid when money
arrives. An entry becomes payable only after a **Funding Event**, which is the
first of the following to occur:

| Funding Event | What triggers it | What is paid |
| :-- | :-- | :-- |
| **Financing** | EV closes an equity or debt financing of at least C$500,000, in one closing or several within 12 months | All Accrued entries, up to the pool ceiling, within 90 days of the closing |
| **Designated funds** | EV receives a grant, sponsorship, or programme funds designated for contributor rewards, or that EV allocates to them | Accrued entries, to the extent of those funds |
| **Commercial revenue** | Cumulative cash receipts from EV's commercial offerings built on this project reach C$250,000 | From then on, EV sets aside 5% of those receipts each quarter until all Accrued entries are paid |

- EV has no obligation to seek or create a Funding Event. Once one occurs, EV
  applies funds as this section sets out.
- EV records each Funding Event in LEDGER.md within 30 days, stating its type
  and the amount applied. EV need not name the source where it is confidential.
- Funds that come with their own eligibility rules are applied only to entries
  those rules allow. Other entries wait for the next Funding Event.
- Funds are applied to Accrued entries in order of acceptance date. If funds
  are short, entries accepted in the same batch are paid pro rata.
- Entries carry no interest, are not transferable, and are not secured.
- **Sunset:** entries still unpaid on 31 March 2028 become recognition-only and
  are marked **Lapsed**.
- Payment may be made in CAD or, where the contributor agrees, in cloud or
  compute credits supplied by a sponsor.

## 5. Nature of the arrangement

- A bounty is a reward for accepted work. It is not wages, a salary, a
  retainer, equity, an option, a revenue share, or a token, and it creates no
  employment, contractor, or agency relationship.
- Setting aside receipts under section 4 funds the pool. It gives no
  contributor a share of revenue: an entry is worth its nominal value and no
  more.
- The work is licensed under the CLA (CLA.md) or CCLA (CCLA.md), whether or not
  a ledger value is paid. CLA.md section 12 sets the express terms of any
  reward and governs if this document conflicts with it.
- Contributors keep copyright in bounty work, except on a bounty issue marked
  as a **Funded Deliverable** before it is claimed. For those, copyright is
  assigned to EV on acceptance, with a licence back to the contributor
  (CLA.md section 12.6).
- Contributors are responsible for their own taxes. EV may withhold or report
  amounts where the law requires.
- EV may decline or reduce an entry where work breaches CONTRIBUTION-SCOPE.md,
  HANDLING.md, or the Code of Conduct, or where law or an employer's or
  institution's policy prevents payment.

## 6. Disputes

Raise a dispute with the maintainers in MAINTAINERS.md. The steward decides. BC law governs, as in the CLA.
