"""The inboxes outreach is sent from and replies are read from.

Your main one (MAIL_ADDRESS / MAIL_APP_PASSWORD), plus up to three more
(MAIL_EXTRA_1_ADDRESS / MAIL_EXTRA_1_PASSWORD ... _3_), all set on the panel's
Settings. Extra inboxes are usually on look-alike domains (scalardigital.uk,
getscalar.co.uk) so a busy sending day never risks your main domain's
reputation. Every inbox uses the same mail host and sender name.

Warm a new inbox up before it sends outreach: 3-4 weeks of normal back-and-forth
email, then start at 10 a day.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

EXTRA_SLOTS = 3


@dataclass(frozen=True)
class Account:
    address: str
    password: str

    def env(self, base: dict | None = None) -> dict:
        """The mail settings with this inbox's login swapped in."""
        return {**(os.environ if base is None else base), "MAIL_ADDRESS": self.address, "MAIL_APP_PASSWORD": self.password}


def accounts(env: dict | None = None) -> list[Account]:
    """Main inbox first, then any extras with both an address and a password."""
    env = os.environ if env is None else env
    out: list[Account] = []
    pairs = [("MAIL_ADDRESS", "MAIL_APP_PASSWORD")] + [
        (f"MAIL_EXTRA_{i}_ADDRESS", f"MAIL_EXTRA_{i}_PASSWORD") for i in range(1, EXTRA_SLOTS + 1)
    ]
    for a, p in pairs:
        address = (env.get(a) or "").strip().lower()
        password = re.sub(r"\s+", "", env.get(p) or "")
        if address and password and address not in {x.address for x in out}:
            out.append(Account(address, password))
    return out
