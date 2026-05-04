"""Module 23 — Cloud Security."""
from __future__ import annotations

from ui import BaseModule, run_subprocess


class Page(BaseModule):
    NAME = "Cloud Security"
    ICON = "☁"
    DESCRIPTION = ("AWS / GCP / Azure CLI inventory checks: public buckets, IAM users, "
                   "open security groups, public IPs, billing surprises.")

    def build(self):
        self.add_action("📋 AWS caller identity",  self.aws_who, primary=True)
        self.add_action("🗂  AWS S3 buckets",       self.aws_buckets)
        self.add_action("🌐 AWS public security groups", self.aws_sg)
        self.add_action("👥 AWS IAM users",         self.aws_iam)
        self.add_action("📊 GCP projects",          self.gcp_projects)
        self.add_action("📊 Azure subscriptions",   self.az_subs)

    def aws_who(self):
        if not self.need("aws"): return
        rc, out = run_subprocess(["aws","sts","get-caller-identity"], timeout=15)
        self.write(out)

    def aws_buckets(self):
        if not self.need("aws"): return
        rc, out = run_subprocess(["aws","s3api","list-buckets","--query",
                                   "Buckets[].Name","--output","text"], timeout=30)
        self.write(out)
        for b in out.split():
            rc, acl = run_subprocess(["aws","s3api","get-bucket-acl","--bucket",b], timeout=15)
            if "AllUsers" in acl or "AuthenticatedUsers" in acl:
                self.write(f"⚠  PUBLIC bucket: {b}")

    def aws_sg(self):
        if not self.need("aws"): return
        rc, out = run_subprocess(
            ["aws","ec2","describe-security-groups","--query",
             "SecurityGroups[?IpPermissions[?contains(IpRanges[].CidrIp,`0.0.0.0/0`)]].[GroupId,GroupName,Description]",
             "--output","table"], timeout=30)
        self.write(out)

    def aws_iam(self):
        if not self.need("aws"): return
        rc, out = run_subprocess(["aws","iam","list-users","--output","table"], timeout=30)
        self.write(out)

    def gcp_projects(self):
        if not self.need("gcloud"): return
        rc, out = run_subprocess(["gcloud","projects","list"], timeout=30); self.write(out)

    def az_subs(self):
        if not self.need("az"): return
        rc, out = run_subprocess(["az","account","list","-o","table"], timeout=30); self.write(out)
