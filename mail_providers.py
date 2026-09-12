"""Disposable-mail providers for MEGA account registration.

Each provider implements the same throwaway-inbox model: create a disposable
inbox, then poll it for MEGA's registration email and return the confirmation
link. Everything talks to the provider's public HTTP API (no keys required).

Uniform interface:

    provider.create()                    -> self   (create the inbox)
    provider.inbox()                     -> str    (address used as MEGA email)
    provider.credential()                -> (pw, id) (lookback fields for CSV)
    provider.get_verification_link(...)  -> str|None (poll for the confirm link)

Provider availability is best-effort: the free services rate-limit and block
datacenter IPs at will. `get_verification_link` never raises -- a provider that
is down simply times out so callers can fall through to the next one.
"""

import random
import re
import string
import time

import requests

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
_URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+")


def first_url(text):
    """Return the first http(s) URL in a blob of text, or None."""
    if not text:
        return None
    m = _URL_RE.search(text)
    return m.group(0) if m else None


class MailProvider:
    provider_name = "base"

    def create(self):
        """Create the inbox. Raise on failure."""
        raise NotImplementedError

    def inbox(self):
        """Return the inbox email address."""
        raise NotImplementedError

    def credential(self):
        """Return (password_field, id_field) for the accounts.csv lookback cols."""
        return ("-", "-")

    def get_verification_link(self, timeout=180, poll=5):
        """Poll the inbox until MEGA's verification link arrives. Never raises."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                link = self._poll_link()
            except Exception:
                link = None
            if link:
                return link
            time.sleep(poll)
        return None

    def _poll_link(self):
        """Return the confirmation link if it has arrived, else None."""
        raise NotImplementedError


class MailTmProvider(MailProvider):
    provider_name = "mailtm"

    def create(self):
        import pymailtm
        self._acc = pymailtm.MailTm().get_account()
        return self

    def inbox(self):
        return self._acc.address

    def credential(self):
        return (self._acc.password, self._acc.id_)

    def _poll_link(self):
        import pymailtm
        from pymailtm.pymailtm import CouldNotGetAccountException, CouldNotGetMessagesException
        try:
            acc = pymailtm.Account(self._acc.id_, self._acc.address, self._acc.password)
            msgs = acc.get_messages()
        except (CouldNotGetAccountException, CouldNotGetMessagesException):
            return None
        for m in msgs or []:
            link = first_url(getattr(m, "text", "") or "")
            if link:
                return link
        return None


class GuerrillaMailProvider(MailProvider):
    provider_name = "guerrillamail"
    API = "https://api.guerrillamail.com/ajax.php"

    def create(self):
        r = requests.get(self.API, params={"f": "get_email_address"}, headers=_UA, timeout=20)
        r.raise_for_status()
        d = r.json()
        self._sid = d["sid_token"]
        self._addr = d["email_addr"]
        return self

    def inbox(self):
        return self._addr

    def credential(self):
        return (self._sid, self._addr)

    def _poll_link(self):
        r = requests.get(
            self.API,
            params={"f": "check_email", "sid_token": self._sid, "seq": 0},
            headers=_UA,
            timeout=20,
        )
        r.raise_for_status()
        for m in r.json().get("list", []):
            # skip GuerrillaMail's own welcome message; MEGA is the only other sender
            if "guerrillamail" in (m.get("mail_from", "") or "").lower():
                continue
            link = first_url(m.get("mail_body", "") or "")
            if link:
                return link
        return None


class OneSecMailProvider(MailProvider):
    provider_name = "1secmail"
    API = "https://www.1secmail.com/api/v1/"

    def create(self):
        r = requests.get(self.API, params={"action": "genRandomMailbox", "count": 1}, headers=_UA, timeout=20)
        r.raise_for_status()
        self._login, self._domain = r.json()[0]
        return self

    def inbox(self):
        return f"{self._login}@{self._domain}"

    def credential(self):
        return (self._domain, self._login)

    def _poll_link(self):
        r = requests.get(
            self.API,
            params={"action": "getMessages", "login": self._login, "domain": self._domain},
            headers=_UA,
            timeout=20,
        )
        r.raise_for_status()
        msgs = r.json()
        if not msgs:
            return None
        r2 = requests.get(
            self.API,
            params={
                "action": "readMessage",
                "login": self._login,
                "domain": self._domain,
                "id": msgs[0]["id"],
            },
            headers=_UA,
            timeout=20,
        )
        r2.raise_for_status()
        m = r2.json()
        return first_url((m.get("textBody") or "") + " " + (m.get("htmlBody") or ""))


class MailGwProvider(MailProvider):
    provider_name = "mailgw"
    API = "https://api.mail.gw"

    def create(self):
        r = requests.get(self.API + "/domains", headers=_UA, timeout=20)
        r.raise_for_status()
        domains = r.json()["hydra:member"]
        domain = domains[0]["domain"]
        user = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(12))
        pw = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
        r2 = requests.post(
            self.API + "/accounts",
            headers=_UA,
            json={"address": f"{user}@{domain}", "password": pw},
            timeout=20,
        )
        r2.raise_for_status()
        d = r2.json()
        self._token = d["token"]
        self._id = d["id"]
        self._addr = d["address"]
        return self

    def inbox(self):
        return self._addr

    def credential(self):
        return (self._token, self._id)

    def _poll_link(self):
        h = dict(_UA)
        h["Authorization"] = f"Bearer {self._token}"
        r = requests.get(f"{self.API}/accounts/{self._id}/messages", headers=h, timeout=20)
        r.raise_for_status()
        msgs = r.json()["hydra:member"]
        if not msgs:
            return None
        r2 = requests.get(f"{self.API}/messages/{msgs[0]['id']}", headers=h, timeout=20)
        r2.raise_for_status()
        m = r2.json()
        return first_url((m.get("text") or "") + " " + (m.get("html") or ""))


PROVIDERS = {
    "mailtm": MailTmProvider,
    "guerrillamail": GuerrillaMailProvider,
    "1secmail": OneSecMailProvider,
    "mailgw": MailGwProvider,
}

# Order used when --provider auto rotates across providers.
AUTO_ORDER = ["mailtm", "guerrillamail", "mailgw", "1secmail"]
