# Create New Mega Accounts
# saves credentials to a file called accounts.csv

import argparse
import csv
import os
import random
import string
import subprocess
import threading
import time

from faker import Faker
from mail_providers import PROVIDERS, AUTO_ORDER

fake = Faker()


class MailCreationError(Exception):
    """Raised when no disposable inbox could be created."""


# Custom function for checking if the argument is below a certain value
def check_limit(value):
    ivalue = int(value)
    if ivalue <= 8:
        return ivalue
    else:
        raise argparse.ArgumentTypeError(f"You cannot use more than 8 threads.")


# set up command line arguments
parser = argparse.ArgumentParser(description="Create New Mega Accounts")
parser.add_argument(
    "-n",
    "--number",
    type=int,
    default=3,
    help="Number of accounts to create",
)
parser.add_argument(
    "-t",
    "--threads",
    type=check_limit,
    default=None,
    help="Number of threads to use for concurrent account creation",
)
parser.add_argument(
    "-p",
    "--password",
    type=str,
    default=None,
    help="Password to use for all accounts",
)
parser.add_argument(
    "--provider",
    type=str,
    choices=["auto"] + list(PROVIDERS),
    default="auto",
    help="Disposable-mail provider to use (default: auto = rotate across all)",
)
args = parser.parse_args()


def get_random_string(length):
    """Generate a random string with a given length."""
    letters = string.ascii_lowercase + string.ascii_uppercase + string.digits
    return "".join(random.choice(letters) for _ in range(length))


# Round-robin over providers so parallel runs spread load and a single
# down provider doesn't stall the whole batch.
_robin_lock = threading.Lock()
_robin_idx = [0]


def _provider_round_robin():
    """Yield provider instances starting at a thread-safe rotating offset."""
    with _robin_lock:
        start = _robin_idx[0]
        _robin_idx[0] = (_robin_idx[0] + 1) % len(AUTO_ORDER)
    order = AUTO_ORDER[start:] + AUTO_ORDER[:start]
    for name in order:
        yield PROVIDERS[name]()


class MegaAccount:
    def __init__(self, name, password, provider):
        self.name = name
        self.password = password
        self.provider = provider

    def generate_mail(self):
        """Create a disposable inbox (retry with backoff). Raises on final failure."""
        p = self.provider
        for attempt in range(5):
            try:
                p.create()
                self.email = p.inbox()
                print(f"\r> [{p.provider_name}] inbox: {self.email}", end="\033[K", flush=True)
                return
            except Exception:
                print(f"\r> [{p.provider_name}] could not create inbox. Retrying ({attempt + 1} of 5)...")
                time_sleep = ""
                for _ in range(random.randint(8, 15)):
                    time_sleep += ". "
                    print("\r" + time_sleep, end="\033[K", flush=True)
                    time.sleep(1)
        raise MailCreationError(p.provider_name)

    def register(self):
        self.generate_mail()

        print(f"\r> [{self.email}]: Registering account...", end="\033[K", flush=True)

        registration = subprocess.run(
            [
                "megatools",
                "reg",
                "--scripted",
                "--register",
                "--email",
                self.email,
                "--name",
                self.name,
                "--password",
                self.password,
            ],
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.verify_command = registration.stdout
        return self.email

    def verify(self):
        print(f"\r> [{self.email}]: Waiting for verification email...", end="\033[K", flush=True)

        link = self.provider.get_verification_link()
        if link is None:
            print(f"\r> [{self.email}]: Failed to verify account. No verification email arrived.")
            return False

        self.verify_command = str(self.verify_command).replace("@LINK@", link)

        verification = subprocess.run(
            self.verify_command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )
        if "registered successfully!" in str(verification.stdout):
            print(f"\r> [{self.email}] Successfully registered and verified.", end="\033[K", flush=True)
            print(f"\n{self.email} - {self.password}")

            pw_field, id_field = self.provider.credential()
            with open("accounts.csv", "a", newline="") as csvfile:
                csvwriter = csv.writer(csvfile)
                # Usage column records which provider produced the inbox;
                # last two columns keep the inbox credentials for future access.
                csvwriter.writerow(
                    [self.email, self.password, self.provider.provider_name, pw_field, id_field, "-"]
                )
            return True

        print(f"\r> [{self.email}]: Failed to verify account.")
        return False


def new_account():
    if args.password is None:
        password = get_random_string(random.randint(8, 14))
    else:
        password = args.password

    if args.provider == "auto":
        # Try providers in rotation; fall through to the next on create failure.
        for provider in _provider_round_robin():
            acc = MegaAccount(fake.name(), password, provider)
            try:
                acc.register()
            except MailCreationError:
                continue
            break
        else:
            print("All mail providers failed to create an inbox. Try again later.")
            return
        acc.verify()
    else:
        acc = MegaAccount(fake.name(), password, PROVIDERS[args.provider]())
        try:
            acc.register()
        except MailCreationError:
            return
        acc.verify()


if __name__ == "__main__":
    # Check if CSV file exists, and if not create it and add header
    if not os.path.exists("accounts.csv"):
        with open("accounts.csv", "w") as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(["Email", "MEGA Password", "Usage", "Mail.tm Password", "Mail.tm ID", "Purpose"])

    # Check if CSV file is using the correct format
    with open("accounts.csv") as csvfile:
        csvreader = csv.reader(csvfile)
        if next(csvreader) != ["Email", "MEGA Password", "Usage", "Mail.tm Password", "Mail.tm ID", "Purpose"]:
            print("CSV file is not in the correct format. Please use the convert_csv.py script to convert it.")
            exit()

    # Parse arguments and generate accounts accordingly
    if args.threads:
        print(f"Generating {args.number} accounts using {args.threads} threads.")
        threads = []
        for _ in range(args.number):
            t = threading.Thread(target=new_account)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
    else:
        print(f"Generating {args.number} accounts.")
        for _ in range(args.number):
            new_account()
