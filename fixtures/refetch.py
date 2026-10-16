#!/usr/bin/env python3
"""Regenerate fixtures/boards.json using the *same* fetcher the tool runs live.

Why this exists: the first version of these fixtures was written by a separate,
hand-rolled fetcher -- and that fetcher silently swallowed a transport failure and wrote
"0 closed PRs" for a repo that had hundreds (see fixtures/README.md). Keeping a second
fetch path is how a regression baseline goes stale without anyone noticing, so this
script calls `fetch_live()` from the tool itself.

    python3 fixtures/refetch.py owner/name [owner/name ...] > fixtures/boards.json

The verbatim document fixtures are captured separately with plain reads:

    gh api repos/{slug}/readme --jq .content | base64 -d > fixtures/readme_{owner}_{repo}.txt
    gh api repos/{slug}/contents/llms.txt --jq .content | base64 -d > fixtures/llms_{owner}_{repo}.txt
    gh api repos/{slug}/contents/BOUNTIES.md --jq .content | base64 -d > fixtures/bounties_{owner}_{repo}.md
    gh api repos/{slug}/contents/CONTRIBUTING.md --jq .content | base64 -d > fixtures/contributing_{owner}_{repo}.md

Requires an authenticated `gh` CLI.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bounty_vet  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    token = subprocess.run(["gh", "auth", "token"], capture_output=True,
                           text=True).stdout.strip()
    if not token:
        print("no token from `gh auth token`", file=sys.stderr)
        return 2
    out = {}
    for slug in sys.argv[1:]:
        rec = bounty_vet.fetch_live(slug, token)
        res = bounty_vet.classify(rec)
        print(f"# {slug}: {res['verdict']} closed={res['closed_prs']} "
              f"merged={res['merged_prs']}", file=sys.stderr)
        out[slug.replace("/", "_")] = rec
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
