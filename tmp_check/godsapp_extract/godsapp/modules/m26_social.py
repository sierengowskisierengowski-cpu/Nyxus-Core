"""Module 26 — Social Engineering Toolkit (defensive prep)."""
from __future__ import annotations

import textwrap
from pathlib import Path

from ui import BaseModule, run_subprocess


class Page(BaseModule):
    NAME = "Social Engineering"
    ICON = "🎭"
    DESCRIPTION = ("Phishing-awareness lab kit: generate test templates, render landing "
                   "pages, point at gophish/setoolkit if installed. Authorised internal use only.")

    TEMPLATES = {
        "password-reset": (
            "Subject: ⚠ Action required — password reset\n\n"
            "Hi {name},\n\nWe noticed unusual activity on your account. "
            "Please confirm your identity by clicking the link below within 24 hours.\n\n"
            "  → {link}\n\n— IT Security"
        ),
        "package-delivery": (
            "Subject: Your package could not be delivered\n\n"
            "Carrier was unable to deliver order #{order}. "
            "Reschedule via the secure portal: {link}\n"
        ),
        "invoice": (
            "Subject: INVOICE #{n} — overdue\n\n"
            "Please find the attached overdue invoice. Settlement portal: {link}\n"
        ),
    }

    def build(self):
        for k in self.TEMPLATES:
            self.add_action(f"📧 template · {k}", lambda k=k: self.render(k))
        self.add_action("📂 export to ~/nyxus-phishing-lab/", self.export, primary=True)
        self.add_action("ℹ  setoolkit",  self.setoolkit)
        self.add_action("ℹ  gophish",    self.gophish)

    def render(self, k: str):
        t = self.TEMPLATES[k].format(name="<NAME>", link="https://lab.example.test/{}".format(k),
                                      order="ABC-123", n="9472")
        self.write(t)

    def export(self):
        out = Path.home() / "nyxus-phishing-lab"
        out.mkdir(exist_ok=True)
        for k, t in self.TEMPLATES.items():
            (out / f"{k}.eml").write_text(textwrap.dedent(t))
        self.write(f"templates exported → {out}")

    def setoolkit(self):
        rc, out = run_subprocess(["setoolkit","--version"], timeout=5)
        self.write(out or "setoolkit not installed")

    def gophish(self):
        rc, out = run_subprocess(["gophish","--version"], timeout=5)
        self.write(out or "gophish not installed — see https://getgophish.com")
