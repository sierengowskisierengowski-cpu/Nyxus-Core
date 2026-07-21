"""Settings view — full configuration panel."""
from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

import threading
import structlog

log = structlog.get_logger()


class SettingsView(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._build_ui()

    def _build_ui(self) -> None:
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Settings"))
        self.append(header)

        # Sidebar + content split
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_vexpand(True)

        # Settings categories sidebar
        cat_scroll = Gtk.ScrolledWindow()
        cat_scroll.set_size_request(180, -1)
        self._cat_list = Gtk.ListBox()
        self._cat_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._cat_list.add_css_class("boxed-list")
        self._cat_list.set_margin_all(8)
        self._cat_list.connect("row-selected", self._on_cat_selected)
        cat_scroll.set_child(self._cat_list)
        paned.set_start_child(cat_scroll)

        # Settings content
        self._settings_scroll = Gtk.ScrolledWindow()
        self._settings_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._settings_content.set_margin_all(16)
        self._settings_scroll.set_child(self._settings_content)
        paned.set_end_child(self._settings_scroll)
        paned.set_position(180)

        self.append(paned)

        categories = [
            "General", "Honeypot Sources", "Enrichment APIs",
            "Alerts & Notifications", "Classification Rules", "Security",
            "Database", "Storage", "Performance", "Logs", "About",
        ]
        for cat in categories:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=cat)
            lbl.set_xalign(0)
            lbl.set_margin_all(8)
            row._category = cat
            row.set_child(lbl)
            self._cat_list.append(row)

        # Default to first
        self._cat_list.select_row(self._cat_list.get_row_at_index(0))

    def _on_cat_selected(self, lb, row) -> None:
        if not row or not hasattr(row, "_category"):
            return
        self._show_category(row._category)

    def _show_category(self, category: str) -> None:
        child = self._settings_content.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._settings_content.remove(child)
            child = nxt

        builder = getattr(self, f"_build_{category.lower().replace(' ', '_').replace('&', 'and').replace('/', '_')}", None)
        if builder:
            builder()
        else:
            lbl = Gtk.Label(label=f"{category} settings")
            lbl.set_opacity(0.5)
            self._settings_content.append(lbl)

    def _build_general(self) -> None:
        from meli.config import get_config
        cfg = get_config()
        grp = Adw.PreferencesGroup(title="General")

        refresh_row = Adw.SpinRow.new_with_range(5, 300, 5)
        refresh_row.set_title("Auto-refresh interval (seconds)")
        refresh_row.set_value(cfg.get("general", "auto_refresh_seconds", default=30))
        refresh_row.connect("changed", lambda r: cfg.set("general", "auto_refresh_seconds", int(r.get_value())))

        confirm_row = Adw.SwitchRow(title="Confirm before destructive actions")
        confirm_row.set_active(cfg.get("general", "confirm_destructive", default=True))
        confirm_row.connect("notify::active", lambda r, _: cfg.set("general", "confirm_destructive", r.get_active()))

        for row in [refresh_row, confirm_row]:
            grp.add(row)
        self._settings_content.append(grp)

    def _build_security(self) -> None:
        from meli.config import get_config
        cfg = get_config()

        grp = Adw.PreferencesGroup(title="Authentication")

        lock_row = Adw.SpinRow.new_with_range(0, 120, 5)
        lock_row.set_title("Auto-lock timeout (minutes, 0=disabled)")
        lock_row.set_value(cfg.get("auth", "auto_lock_minutes", default=10))
        lock_row.connect("changed", lambda r: cfg.set("auth", "auto_lock_minutes", int(r.get_value())))
        grp.add(lock_row)

        change_pw_btn = Gtk.Button(label="Change Master Password")
        change_pw_btn.add_css_class("suggested-action")
        change_pw_btn.connect("clicked", self._on_change_password)

        totp_btn = Gtk.Button(label="Configure 2FA (TOTP)")
        totp_btn.connect("clicked", self._on_configure_2fa)

        btn_box = Gtk.Box(spacing=8)
        btn_box.set_margin_top(8)
        btn_box.append(change_pw_btn)
        btn_box.append(totp_btn)

        self._settings_content.append(grp)
        self._settings_content.append(btn_box)

    def _build_enrichment_apis(self) -> None:
        from meli.config import get_config
        cfg = get_config()
        grp = Adw.PreferencesGroup(title="Enrichment API Keys")

        services = [
            ("abuseipdb", "AbuseIPDB"),
            ("greynoise", "GreyNoise"),
            ("virustotal", "VirusTotal"),
            ("shodan", "Shodan"),
            ("ipinfo", "IPInfo"),
        ]
        for key, label in services:
            row = Adw.PasswordEntryRow(title=f"{label} API Key")
            current = cfg.get("enrichment", "services", key, "api_key") or ""
            row.set_text(current)
            def _save(entry, k=key):
                val = entry.get_text()
                cfg.set("enrichment", "services", k, "api_key", val)
                cfg.set("enrichment", "services", k, "enabled", bool(val))
            row.connect("changed", _save)
            grp.add(row)

        geo_grp = Adw.PreferencesGroup(
            title="GeoIP (MaxMind GeoLite2)",
            description=(
                "Required for the Geographic Map view and country/ASN tagging. "
                "Get a free license key at maxmind.com (no credit card required)."
            ),
        )

        maxmind_row = Adw.PasswordEntryRow(title="MaxMind License Key")
        maxmind_row.set_text(cfg.get("enrichment", "maxmind_license_key") or "")
        maxmind_row.connect("changed", lambda r: cfg.set("enrichment", "maxmind_license_key", r.get_text()))
        geo_grp.add(maxmind_row)

        self._geoip_city_row = Adw.ActionRow(title="GeoLite2-City")
        self._geoip_asn_row = Adw.ActionRow(title="GeoLite2-ASN")
        self._geoip_auto_row = Adw.ActionRow(title="Auto-update")
        geo_grp.add(self._geoip_city_row)
        geo_grp.add(self._geoip_asn_row)
        geo_grp.add(self._geoip_auto_row)
        self._refresh_geoip_status_rows()

        self._update_geo_btn = Gtk.Button(label="Download / Update GeoLite2 Databases Now")
        self._update_geo_btn.set_margin_top(8)
        self._update_geo_btn.connect("clicked", self._on_update_geoip)

        self._settings_content.append(grp)
        self._settings_content.append(geo_grp)
        self._settings_content.append(self._update_geo_btn)

    def _refresh_geoip_status_rows(self) -> None:
        from meli.config import get_config
        from meli.enrichment.geolocation import get_geoip_status
        from meli.utils.helpers import format_bytes
        status = get_geoip_status()
        for label, row in (("city", self._geoip_city_row), ("asn", self._geoip_asn_row)):
            if status[f"{label}_present"]:
                updated = status[f"{label}_updated"] or "—"
                # Trim trailing "+00:00" for readability
                updated = updated.replace("+00:00", " UTC")
                row.set_subtitle(
                    f"✓ Installed · {format_bytes(status[f'{label}_size'])} · "
                    f"updated {updated}"
                )
            else:
                row.set_subtitle("✗ Not downloaded — enter your license key and click Download below")

        auto_row = getattr(self, "_geoip_auto_row", None)
        if auto_row is not None:
            cfg = get_config()
            enabled = cfg.get("enrichment", "geoip_auto_update_enabled", default=True)
            interval = cfg.get("enrichment", "geoip_auto_update_interval_days", default=7)
            last_at = cfg.get("enrichment", "geoip_last_auto_update_at")
            last_status = cfg.get("enrichment", "geoip_last_auto_update_status")
            last_error = cfg.get("enrichment", "geoip_last_auto_update_error")

            if not enabled:
                auto_row.set_subtitle("Disabled")
            elif not last_at:
                auto_row.set_subtitle(
                    f"Scheduled every {interval} day(s) · no run yet "
                    "(runs while the ingest daemon is up and a license key is set)"
                )
            else:
                pretty = str(last_at).replace("+00:00", " UTC")
                if last_status == "success":
                    auto_row.set_subtitle(f"✓ Last auto-update: {pretty} (success)")
                elif last_status == "skipped_no_key":
                    auto_row.set_subtitle(f"Last attempt: {pretty} (skipped — no license key)")
                else:
                    detail = f" — {last_error}" if last_error else ""
                    auto_row.set_subtitle(f"✗ Last auto-update: {pretty} (failure{detail})")

    def _build_alerts_and_notifications(self) -> None:
        from meli.config import get_config
        cfg = get_config()
        grp = Adw.PreferencesGroup(title="Notification Channels")

        fields = [
            ("discord_webhook", "Discord Webhook URL"),
            ("slack_webhook", "Slack Webhook URL"),
            ("telegram_bot_token", "Telegram Bot Token"),
            ("telegram_chat_id", "Telegram Chat ID"),
            ("email_smtp_host", "SMTP Host"),
            ("email_from", "From Email"),
            ("email_to", "To Email"),
        ]
        self._test_btns: dict[str, Gtk.Button] = {}
        for cfg_key, label in fields:
            row = Adw.EntryRow(title=label)
            row.set_text(str(cfg.get("alerts", cfg_key) or ""))
            def _save(entry, k=cfg_key):
                cfg.set("alerts", k, entry.get_text() or None)
            row.connect("changed", _save)
            grp.add(row)

        sound_row = Adw.SwitchRow(title="Sound Alerts")
        sound_row.set_active(cfg.get("alerts", "sound_enabled", default=True))
        sound_row.connect("notify::active", lambda r, _: cfg.set("alerts", "sound_enabled", r.get_active()))
        grp.add(sound_row)

        test_box = Gtk.Box(spacing=8)
        test_box.set_margin_top(8)
        for label, channel in [("Test Discord", "discord"), ("Test Slack", "slack"),
                                ("Test Telegram", "telegram")]:
            btn = Gtk.Button(label=label)
            ch = channel
            btn.connect("clicked", lambda _, c=ch: self._test_notification(c))
            test_box.append(btn)

        self._settings_content.append(grp)
        self._settings_content.append(test_box)

    def _build_honeypot_sources(self) -> None:
        grp = Adw.PreferencesGroup(title="Configured Honeypots")
        add_btn = Gtk.Button(label="Add Honeypot Source")
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", self._on_add_honeypot)
        self._hp_group = grp
        self._settings_content.append(grp)
        self._settings_content.append(add_btn)
        threading.Thread(target=self._load_honeypots, daemon=True).start()

    def _load_honeypots(self) -> None:
        from meli.database import get_db
        from meli.database.models import Honeypot
        from sqlalchemy import select
        with get_db() as db:
            hps = db.execute(select(Honeypot)).scalars().all()
            data = [(h.id, h.name, h.honeypot_type, h.enabled, h.ingest_token, h.total_events_received) for h in hps]
        GLib.idle_add(self._populate_honeypots, data)

    def _populate_honeypots(self, data: list) -> bool:
        child = self._hp_group.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._hp_group.remove(child)
            child = nxt
        for hid, name, htype, enabled, token, events in data:
            row = Adw.ActionRow(
                title=f"{name} ({htype})",
                subtitle=f"Events: {events} — Token: {(token or '')[:12]}..."
            )
            sw = Gtk.Switch()
            sw.set_active(enabled)
            sw.set_valign(Gtk.Align.CENTER)
            row.add_suffix(sw)
            self._hp_group.add(row)
        if not data:
            self._hp_group.add(Adw.ActionRow(title="No honeypots configured"))
        return False

    def _build_database(self) -> None:
        from meli.database.backup import get_database_stats
        try:
            stats = get_database_stats()
        except Exception:
            stats = {}

        grp = Adw.PreferencesGroup(title="Database")
        grp.add(Adw.ActionRow(title="Location", subtitle=stats.get("path", "—")))
        grp.add(Adw.ActionRow(title="Size", subtitle=stats.get("size_human", "—")))
        for table, count in (stats.get("table_counts") or {}).items():
            grp.add(Adw.ActionRow(title=f"  {table}", subtitle=f"{count:,} rows"))

        btn_box = Gtk.Box(spacing=8)
        btn_box.set_margin_top(8)
        backup_btn = Gtk.Button(label="Backup Now")
        backup_btn.connect("clicked", self._on_backup)
        vacuum_btn = Gtk.Button(label="Vacuum Database")
        vacuum_btn.connect("clicked", self._on_vacuum)
        btn_box.append(backup_btn)
        btn_box.append(vacuum_btn)

        self._settings_content.append(grp)
        self._settings_content.append(btn_box)

    def _build_about(self) -> None:
        grp = Adw.PreferencesGroup(title="About Meli")
        for k, v in [
            ("Application", "Meli — Honeypot Command Center"),
            ("Version", "1.0.0"),
            ("Author", "Joseph Sierengowski"),
            ("License", "MIT"),
            ("Repository", "https://github.com/sierengowski/meli"),
        ]:
            grp.add(Adw.ActionRow(title=k, subtitle=v))
        self._settings_content.append(grp)

    def _on_change_password(self, _) -> None:
        from meli.ui.dialogs.change_password import ChangePasswordDialog
        dialog = ChangePasswordDialog(transient_for=self.get_root())
        dialog.present()

    def _on_configure_2fa(self, _) -> None:
        pass  # TODO: TOTP configuration dialog

    def _on_add_honeypot(self, _) -> None:
        import socket
        from meli.config import get_config
        cfg = get_config()
        port = cfg.get("http_ingest", "port", default=17654)

        # Check daemon health before opening dialog
        daemon_ok = False
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                daemon_ok = True
        except OSError:
            daemon_ok = False

        root = self.get_root()

        if not daemon_ok:
            dlg = Adw.AlertDialog(
                heading="Ingest Daemon Not Running",
                body=(
                    f"The Meli ingest daemon is not reachable on port {port}.\n\n"
                    "Start it before adding a honeypot source:\n"
                    "    systemctl --user start meli-ingest\n\n"
                    "Or check logs with:\n"
                    "    journalctl --user -u meli-ingest -n 50"
                ),
            )
            dlg.add_response("ok", "OK")
            dlg.present(root)
            return

        _AddHoneypotDialog(transient_for=root, on_saved=self._reload_honeypots).present()

    def _reload_honeypots(self) -> None:
        threading.Thread(target=self._load_honeypots, daemon=True).start()

    def _test_notification(self, channel: str) -> None:
        def _run():
            from meli.alerts import notifiers
            if channel == "discord":
                from meli.config import get_config
                url = get_config().get("alerts", "discord_webhook")
                if url:
                    notifiers.discord.test(url)
            elif channel == "slack":
                from meli.config import get_config
                url = get_config().get("alerts", "slack_webhook")
                if url:
                    notifiers.slack.test(url)
        threading.Thread(target=_run, daemon=True).start()

    def _on_update_geoip(self, _) -> None:
        from meli.config import get_config
        key = get_config().get("enrichment", "maxmind_license_key")
        if not key:
            self._show_info("Enter your MaxMind license key first.\nGet a free one at maxmind.com.")
            return
        output_dir = str(get_config().data_dir / "geoip")
        btn = getattr(self, "_update_geo_btn", None)
        if btn:
            btn.set_sensitive(False)
            btn.set_label("Downloading GeoLite2 databases…")

        def _run():
            from meli.enrichment.geolocation import download_geolite2
            ok = download_geolite2(key, output_dir)
            GLib.idle_add(self._geoip_update_done, ok)
        threading.Thread(target=_run, daemon=True).start()

    def _geoip_update_done(self, success: bool) -> bool:
        btn = getattr(self, "_update_geo_btn", None)
        if btn:
            btn.set_sensitive(True)
            btn.set_label("Download / Update GeoLite2 Databases Now")
        if hasattr(self, "_geoip_city_row"):
            self._refresh_geoip_status_rows()
        self._show_info(
            "GeoLite2 databases downloaded successfully."
            if success
            else "Download failed — check your license key and internet connection."
        )
        return False

    def _on_backup(self, _) -> None:
        def _run():
            from meli.database.backup import backup_database
            path = backup_database()
            GLib.idle_add(self._show_info, f"Backup saved to:\n{path}")
        threading.Thread(target=_run, daemon=True).start()

    def _on_vacuum(self, _) -> None:
        def _run():
            from meli.database.backup import vacuum_database
            vacuum_database()
            GLib.idle_add(self._show_info, "Database vacuumed successfully")
        threading.Thread(target=_run, daemon=True).start()

    def _show_info(self, msg: str) -> None:
        dialog = Adw.MessageDialog(heading="Done", body=msg)
        dialog.add_response("ok", "OK")
        top = self.get_root()
        if top: dialog.set_transient_for(top)
        dialog.present()


class _AddHoneypotDialog(Adw.Dialog):
    """Dialog for registering a new honeypot source."""

    HONEYPOT_TYPES = ["cowrie", "heralding", "dionaea", "glastopf", "mailoney", "generic_json"]
    INGEST_METHODS = ["mqtt", "http", "logfile"]

    def __init__(self, transient_for=None, on_saved=None):
        super().__init__(title="Add Honeypot Source", content_width=420)
        self._on_saved = on_saved
        self._build_ui()
        if transient_for:
            self.set_transient_for(transient_for)

    def _build_ui(self) -> None:
        import uuid
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.set_margin_start(20)
        box.set_margin_end(20)

        grp = Adw.PreferencesGroup(title="Honeypot Details")

        # Name
        self._name_row = Adw.EntryRow(title="Name (e.g. london-ssh-01)")
        grp.add(self._name_row)

        # Type
        type_row = Adw.ComboRow(title="Honeypot Type")
        type_model = Gtk.StringList.new(self.HONEYPOT_TYPES)
        type_row.set_model(type_model)
        self._type_row = type_row
        grp.add(type_row)

        # Ingest method
        method_row = Adw.ComboRow(title="Ingestion Method")
        method_model = Gtk.StringList.new(self.INGEST_METHODS)
        method_row.set_model(method_model)
        self._method_row = method_row
        grp.add(method_row)

        # Token (auto-generated, shown read-only)
        self._token = str(uuid.uuid4()).replace("-", "")
        token_row = Adw.ActionRow(
            title="Ingest Token",
            subtitle=self._token,
        )
        token_row.add_css_class("monospace")
        grp.add(token_row)

        box.append(grp)

        # Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda _: self.close())

        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save)

        btn_box.append(cancel_btn)
        btn_box.append(save_btn)
        box.append(btn_box)

        self.set_child(box)

    def _on_save(self, _) -> None:
        name = self._name_row.get_text().strip()
        if not name:
            self._name_row.add_css_class("error")
            return

        hp_type = self.HONEYPOT_TYPES[self._type_row.get_selected()]
        method = self.INGEST_METHODS[self._method_row.get_selected()]

        def _save():
            from meli.database import get_db
            from meli.database.models import Honeypot
            with get_db() as db:
                hp = Honeypot(
                    name=name,
                    honeypot_type=hp_type,
                    ingest_method=method,
                    ingest_token=self._token,
                    enabled=True,
                )
                db.add(hp)
            log.info("Honeypot source added", name=name, type=hp_type, method=method)
            GLib.idle_add(self._finish)

        import threading
        threading.Thread(target=_save, daemon=True).start()

    def _finish(self) -> bool:
        self.close()
        if self._on_saved:
            self._on_saved()
        return False
