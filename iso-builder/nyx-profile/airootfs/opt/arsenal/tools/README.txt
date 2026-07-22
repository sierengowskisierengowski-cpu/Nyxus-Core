Arsenal external tool roots.

The service-style tools (jeTT, Bifrost, Meli, honeypot) ship at their own
canonical locations (/usr, /opt/meli, /opt/honeypot) and are wired via the
Arsenal registry directly.

The training/web tools (GSL, RedForge, Forge, CIPHER, AI-Cyber-Defense-Trainer,
axiom, c2) live under /opt/arsenal/tools/<name>. Their source ships on the ISO,
but each app's own setup (deps, DB role/database, migrations, admin seed) has
NOT been run yet — no secrets or databases are baked in on purpose. After
install, run:

    bash ~/Arsenal/setup-apps.sh
    (or: /usr/local/bin/nyxus-setup-apps)

once to bring the web stack up. It is idempotent — safe to re-run. Re-bake
with NYX_STAGE_ARSENAL_APPS=1 to refresh these trees from a newer local
checkout at ~/GowskiNet-Vault or ~/Projects (see build-iso.sh).
