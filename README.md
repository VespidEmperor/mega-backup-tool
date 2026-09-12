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

> Use it only with links and files you own or have permission to copy.

---

## Quick start

```bash
# one-shot setup (Windows: setup.bat  /  macos+linux: ./setup.sh)
setup.bat

# create 3 accounts (they appear in accounts.csv, all auto-verified)
python generate_accounts.py
```

That's it. See **Troubleshooting** at the bottom if a step errors.

---

## Prerequisites (what `setup.bat` / `setup.sh` does for you)

- **Python 3.6+** on your `PATH`.
- Python deps: `python -m pip install -r requirements.txt`
  (`python -m pip`, not bare `pip`, so it targets the same interpreter `python` uses).
  `server_copy.py` additionally needs `mega.py` — installed via
  `python -m pip install --no-deps "mega.py==1.0.8"` (see note below on why
  `--no-deps`); the `setup` scripts do both steps for you.
- **megatools** on your `PATH` (a standalone binary, *not* a pip package —
  that's why it isn't a `requirements.txt` line).
  - Windows: `setup.bat` downloads and installs it automatically.
    Manual: unzip `megatools-*-win64.zip` from
    <https://xff.cz/megatools/builds/builds/>, then add the folder with
    `megatools.exe` to your Windows `PATH`.
  - Linux: `sudo apt install megatools` (or `dnf install megatools`).
  - Check with: `megatools --version`

---

## Usage

### 1. Create accounts

```bash
python generate_accounts.py                 # 3 accounts (default)
python generate_accounts.py -n 10           # 10 accounts, sequential (safest vs rate limits)
python generate_accounts.py -n 5 -p "pw"    # 5 accounts, shared password

# choose a disposable-mail provider (default: auto = rotate across all)
python generate_accounts.py --provider mailtm
python generate_accounts.py --provider guerrillamail
python generate_accounts.py --provider 1secmail
python generate_accounts.py --provider mailgw
```

Supported mail providers:

| Provider | Flag | Notes |
|---|---|---|
| Mail.tm | `mailtm` | original provider; rotates domains (@uberip.com, …) |
| GuerrillaMail | `guerrillamail` | no-account inbox via public API |
| 1secmail | `1secmail` | simplest API; often blocked from datacenter IPs |
| mail.gw (MailGorilla) | `mailgw` | Mail.tm-compatible standalone service |

`--provider auto` (default) round-robins across all providers so parallel runs
spread the load, and if one provider fails to create an inbox it falls through
to the next instead of aborting the whole batch. Pin `--provider` to a single
provider when you know only one is reachable from your IP.

Each account is registered and email-verified automatically. Credentials are
appended to `accounts.csv`:

| Column | Meaning |
|---|---|
| `Email` | MEGA login (a disposable mail.tm address) |
| `MEGA Password` | the password you log in with |
| `Usage` | free-text label — records which mail provider created the inbox (`mailtm`/`guerrillamail`/`1secmail`/`mailgw`) |
| `Mail.tm Password` / `Mail.tm ID` | the disposable inbox credential (kept for future access; columns are legacy-named) |
| `Purpose` | free-text |

### 2. Keep accounts alive

MEGA deletes accounts that go ~3 months without a login. Log them all in on a
schedule (run monthly via cron/Task Scheduler):

```bash
python signin_accounts.py
```

### 3. Mirror a link into a backup account (server-side)

Write a plan file (`copy_plan.csv`) — one line per copy:

```csv
target_email,target_password,source_link
```

Example:

```csv
backup1@example.com,SuperSecret123,https://mega.nz/file/AbCdEfGh#decryption-key
```

Run it:

```bash
python server_copy.py --plan copy_plan.csv --verify
```

Results append to `backup_log.csv` (`node_handle`, `status`, `verify`).
`--verify` re-lists the target via `megatools` after each import to confirm the
node actually landed (don't just trust the API's self-report).

### 4. (legacy) Convert an old CSV

```bash
python convert_csv.py -i old_accounts.csv
```

---

## How the server-side copy works

A MEGA link is `https://mega.nz/file/<HANDLE>#<KEY>`. `HANDLE` addresses the
encrypted node; `KEY` is its decryption key. `server_copy.py` calls MEGA's `p`
(put) operation on the target account, passing the public handle plus the key
re-encrypted under the target's master key. MEGA links the existing encrypted
blob into the target account — the content is never downloaded locally.

This works for **files via their `#`-key link**. Folder imports (MEGA-nested
key derivation) aren't covered here.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'pymailtm'` (or `faker`, `mega`)**
You installed deps with a different Python than the one you're running with.
Use `python -m pip install -r requirements.txt` (same `python` you run the
script with) rather than bare `pip`.

**`module 'asyncio' has no attribute 'coroutine'` (or similar, in `tenacity`)**
You have the old `tenacity` 5.x that the `mega.py` package pulls in; it's broken
on Python 3.11+. Fix: `python -m pip install "tenacity>=8.0.0"` (and
`pycryptodome`). The `setup` scripts already install a modern tenacity and use
`--no-deps` for `mega.py` so its stale `tenacity<6` pin doesn't take effect.

**`megatools` is not recognized / it fails at account registration**
`megatools` isn't on `PATH`. Run `setup.bat` (it downloads megatools and adds it
to `PATH`), then **reopen** the terminal (PATH changes only apply to new
shells). On Linux, `sudo apt install megatools`.

**"Could not get [provider] account" / "All mail providers failed"**
A disposable-mail service is rate-limiting or blocking your IP. `--provider auto`
falls through to the next provider automatically; for a fixed provider, run
sequentially (no `-t`), space batches out, and wait a few minutes. Some
providers block non-residential IPs outright (see the provider table above).

**Account works today but dies later**
MEGA deletes accounts inactive ~3 months and can suspend disposable-email
signups. Treat these as mirrors, not your only copy; run `signin_accounts.py`
monthly.

---

## Notes & caveats

- **Credentials are plaintext** in `accounts.csv` / `backup_log.csv` (both
  git-ignored). Treat as secrets.
- **Disposable-email + bulk `megatools reg` signups are against MEGA's ToS**
  for those accounts. Don't use this to store anything you don't have the
  right to.

## License

MIT. Based on
[f-o/MEGA-Account-Generator](https://github.com/f-o/MEGA-Account-Generator)
(account/mail layer) and the `megatools` client. See `LICENSE`.
