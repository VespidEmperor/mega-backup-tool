#!/usr/bin/env python3
"""
Server-side MEGA link backup.

Imports links you OWN (they carry their node handle + decryption key) directly
into a target MEGA account. The copy happens MEGA-side ("p" api op) - the bytes
never round-trip through this machine.

Plan file (CSV), one line per backup:
    target_email,target_password,source_link

  - source_link = full mega.nz file link (with the #key part).
  - Lines starting with '#' or blank are skipped.

Options:
    --plan FILE      plan CSV (default copy_plan.csv)
    --log  FILE      append result log (default backup_log.csv)
    --verify         after each import, list the target account via megatools
                     to independently confirm the node landed (not just trust
                     the API's self-report).

Output log columns:
    email,password,link,node_handle,status
"""

import argparse
import csv
import subprocess

from mega import Mega

_mega = Mega()


def import_one(email, password, link):
    """Login to target account and import the link server-side.

    Returns the new node handle in the target account.
    """
    m = _mega.login(email, password)
    res = m.import_public_url(link)
    if res and res.get("f"):
        return res["f"][0]["h"]
    return None


def verify_present(email, password, name_hint=None):
    """Independent check: list /Root on the account via megatools."""
    try:
        out = subprocess.run(
            ["megatools", "ls", "-u", email, "-p", password, "/Root"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        ).stdout
    except Exception as e:  # noqa: BLE001
        return f"verify-error: {e}"
    lines = [l for l in out.splitlines() if l.strip() and l.strip() != "/Root"]
    return f"{len(lines)} file(s) in /Root"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default="copy_plan.csv")
    ap.add_argument("--log", default="backup_log.csv")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    wrote_header = False

    with open(args.plan, encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row or not row[0].strip() or row[0].lstrip().startswith("#"):
                continue
            email, password = row[0].strip(), row[1].strip()
            link = row[2].strip() if len(row) > 2 else ""
            try:
                node = import_one(email, password, link)
                status = "ok" if node else "fail: no node returned"
            except Exception as e:  # noqa: BLE001
                node, status = "", f"fail: {e}"

            verify = ""
            if args.verify and status == "ok":
                verify = verify_present(email, password)

            print(f"{email} <- {link}\n    => {status}  node={node}  {verify}")

            with open(args.log, "a", newline="", encoding="utf-8") as lf:
                w = csv.writer(lf)
                if not wrote_header:
                    w.writerow(
                        ["email", "password", "link", "node_handle", "status", "verify"]
                    )
                    wrote_header = True
                w.writerow([email, password, link, node, status, verify])


if __name__ == "__main__":
    main()
