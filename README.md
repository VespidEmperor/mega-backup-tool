# mega-backup-tool

CLI tooling for managing your own MEGA accounts and mirroring links you own
into a backup account. The mirror step happens **server-side** — MEGA
re-references the encrypted file node, so the bytes never round-trip through
your machine.

Two things, one toolkit:

1. **Account management** — create MEGA accounts, verify them, and log them in
   periodically so they aren't purged for inactivity.
2. **Server-side copy** — import a link you own (it carries its node handle +
   decryption key) straight into another account, bypassing a download and
   re-upload.

## Why

The free MEGA tier gives 20 GiB per account and deletes accounts that stay
inactive ~3 months. If you want a cheap redundant copy of your own files, you
can fan them out across several accounts and keep them alive on a schedule —
this tool automates exactly that.

> Use it only with links and files you own or have permission to copy.

## Prerequisites

- **megatools** — the MEGA command-line client. Install the build for your OS
  and make sure `megatools` is on your `PATH`:
  - Windows: `megatools-*-win64.zip` from <https://xff.cz/megatools/builds/builds/>
  - Linux: `apt install megatools` / `dnf install megatools`
  - Then: `megatools --version`
- **Python 3.6+**
- Install the Python deps:

```bash
pip install -r requirements.txt
```

## Usage

### 1. Create accounts

```bash
# Create 3 accounts (default)
python generate_accounts.py

# Create 10 accounts, sequential (safer than threading against mail.tm rate limits)
python generate_accounts.py -n 10

# Create 5 accounts with a shared password
python generate_accounts.py -n 5 -p "your-password"
```

Each account is registered and email-verified automatically. Credentials are
appended to `accounts.csv`:

| Column | Meaning |
|---|---|
| `Email` | MEGA login (a disposable mail.tm address) |
| `MEGA Password` | the password you log in with |
| `Usage` | free-text label (edit it to track what each account holds) |
| `Mail.tm Password` / `Mail.tm ID` | the disposable inbox (kept for future access) |
| `Purpose` | free-text |

### 2. Keep accounts alive

MEGA deletes accounts that go ~3 months without a login. Log them all in on a
schedule (run this monthly via cron/systemd):

```bash
python signin_accounts.py
```

It reads `accounts.csv` and reports `Successfully logged in` per account.

### 3. Mirror a link into a backup account (server-side)

Write a plan file (`copy_plan.csv`) — one line per copy:

```csv
target_email,target_password,source_link
```

Example:

```csv
backup1@example.com,SuperSecret123,https://mega.nz/file/AbCdEfGh#decryption-key
```

Then run:

```bash
python server_copy.py --plan copy_plan.csv --verify
```

For each row it logs into the target account and imports the link server-side.
Results append to `backup_log.csv`:

| Column | Meaning |
|---|---|
| `node_handle` | the new node handle in the target account |
| `status` | `ok` or the error |
| `verify` | independent `megatools ls` check (with `--verify`) |

Options:

- `--plan FILE` — plan CSV (default `copy_plan.csv`)
- `--log FILE` — result log (default `backup_log.csv`)
- `--verify` — after each import, re-list the target account via `megatools`
  to confirm the node landed (don't just trust the API's self-report)

### 4. (legacy) Convert an old CSV

If you have an `accounts.csv` from before May 2024:

```bash
python convert_csv.py -i old_accounts.csv
```

## How the server-side copy works

A MEGA file/folder link is `https://mega.nz/file/<HANDLE>#<KEY>`. `HANDLE`
addresses the encrypted node; `KEY` is the decryption key. `server_copy.py`
calls MEGA's `p` (put) operation on the target account, passing the public
handle plus the key re-encrypted under the target's master key. MEGA links the
existing encrypted blob into the target account — the content is never
downloaded locally.

This only works for **files via their `#`-key link**. Folder imports differ
(MEGA-nested key derivation) and aren't covered here.

## Notes & caveats

- **Rate limits**: mail.tm throttles rapid account creation (usually after
  ~8 in a burst). Create sequentially (`-n` without `-t`) and pace big batches.
- **Credentials are plaintext** in `accounts.csv` and `backup_log.csv` — both
  are git-ignored. Treat them as secrets and don't publish them.
- **Disposable emails**: accounts are registered with mail.tm addresses; they
  are throwaway by design and can be suspended by MEGA. Use as a mirror, not a
  sole copy.
- **ToS**: bulk `megatools reg` + disposable-email signups are against MEGA's
  terms for the accounts themselves. Don't use this for anything you don't
  have the right to store.

## License

MIT. Based on
[f-o/MEGA-Account-Generator](https://github.com/f-o/MEGA-Account-Generator)
(Python account/mail layer) and the `megatools` client. See `LICENSE`.
