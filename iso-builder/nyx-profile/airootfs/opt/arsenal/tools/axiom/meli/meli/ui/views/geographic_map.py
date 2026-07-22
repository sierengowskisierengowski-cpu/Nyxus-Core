"""Geographic Map view — world map with attack density visualization."""
from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

import threading
import structlog

log = structlog.get_logger()


class GeographicMapView(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Geographic Map"))
        refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh_btn.connect("clicked", lambda _: self.refresh())
        header.pack_end(refresh_btn)
        self.append(header)

        # Main split: map (left/top) + country table (right/bottom)
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_vexpand(True)

        # Map area — try WebKit if available, fallback to ASCII table
        self._map_frame = Gtk.Frame()
        self._map_frame.set_label("World Map")
        self._map_frame.set_hexpand(True)
        self._map_frame.set_vexpand(True)
        self._build_map_widget()
        paned.set_start_child(self._map_frame)

        # Country stats sidebar
        scroll = Gtk.ScrolledWindow()
        scroll.set_size_request(240, -1)
        self._country_list = Gtk.ListBox()
        self._country_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._country_list.add_css_class("boxed-list")
        scroll.set_child(self._country_list)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        title = Gtk.Label(label="Top Countries")
        title.add_css_class("heading")
        title.set_margin_all(8)
        sidebar.append(title)
        sidebar.append(scroll)
        paned.set_end_child(sidebar)
        paned.set_position(900)

        self.append(paned)

    def _build_map_widget(self) -> None:
        """Try WebKitGTK for interactive map, fall back to ASCII heatmap."""
        try:
            gi.require_version("WebKit", "6.0")
            from gi.repository import WebKit
            webview = WebKit.WebView()
            webview.set_hexpand(True)
            webview.set_vexpand(True)
            self._webview = webview
            self._map_frame.set_child(webview)
            self._use_webkit = True
        except Exception:
            self._use_webkit = False
            lbl = Gtk.Label(label=(
                "Interactive map requires WebKitGTK.\n\n"
                "Attack sources are listed in the country table →\n\n"
                "Install webkit2gtk-4.1 for the interactive map."
            ))
            lbl.set_justify(Gtk.Justification.CENTER)
            lbl.set_opacity(0.6)
            lbl.set_vexpand(True)
            lbl.set_valign(Gtk.Align.CENTER)
            self._map_frame.set_child(lbl)

    def refresh(self) -> None:
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self) -> None:
        try:
            from meli.database import get_db
            from meli.database.models import Event
            from sqlalchemy import func, select
            from datetime import datetime, timedelta, timezone
            ago_24h = datetime.now(timezone.utc) - timedelta(hours=24)
            with get_db() as db:
                country_rows = db.execute(
                    select(Event.country_code, func.count(Event.id))
                    .where(Event.country_code.isnot(None))
                    .where(Event.timestamp >= ago_24h)
                    .group_by(Event.country_code)
                    .order_by(func.count(Event.id).desc())
                    .limit(50)
                ).all()

                # Per-source-IP aggregation with real coords. Fall back to the
                # country centroid when an IP has no city-level lat/lon yet.
                ip_rows = db.execute(
                    select(
                        Event.source_ip,
                        Event.country_code,
                        func.max(Event.latitude),
                        func.max(Event.longitude),
                        func.count(Event.id),
                        func.max(Event.severity),
                    )
                    .where(Event.timestamp >= ago_24h)
                    .where(Event.source_ip.isnot(None))
                    .group_by(Event.source_ip)
                    .order_by(func.count(Event.id).desc())
                    .limit(5000)
                ).all()
            GLib.idle_add(self._populate_countries,
                          list(country_rows), list(ip_rows))
        except Exception as e:
            log.error("Geographic map load failed", error=str(e))

    def _populate_countries(self, data: list, ip_rows: list | None = None) -> bool:
        child = self._country_list.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._country_list.remove(child)
            child = nxt

        from meli.utils.helpers import country_flag_emoji
        for country_code, count in data:
            flag = country_flag_emoji(country_code)
            row = Adw.ActionRow(
                title=f"{flag} {country_code}",
                subtitle=f"{count:,} events"
            )
            self._country_list.append(row)

        if not data:
            empty = Adw.ActionRow(title="No geo data yet",
                                   subtitle="Enable GeoIP in Settings for location data")
            self._country_list.append(empty)

        if self._use_webkit and (data or ip_rows):
            self._update_map(data, ip_rows or [])
        return False

    def _update_map(self, data: list, ip_rows: list) -> None:
        """Load a Leaflet.js map with per-IP attacker pins and clustering.

        Each source IP becomes one marker, placed at the city-level lat/lon
        captured at ingest time. IPs without real coords (older events, or
        IPs where GeoLite2-City had no city resolution) fall back to the
        country centroid so the map stays useful during the transition.
        """
        import json
        from meli.utils.helpers import country_centroid, country_flag_emoji

        markers = []
        for ip, code, lat, lon, count, sev in ip_rows:
            if lat is None or lon is None or (lat == 0 and lon == 0):
                centroid = country_centroid(code or "")
                if not centroid:
                    continue
                lat, lon = centroid
                approx = True
            else:
                approx = False
            markers.append({
                "lat": float(lat),
                "lon": float(lon),
                "ip": ip,
                "code": code or "",
                "flag": country_flag_emoji(code or ""),
                "count": int(count),
                "sev": sev or "INFO",
                "approx": approx,
            })

        markers_json = json.dumps(markers)
        html = """<!DOCTYPE html><html><head>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<style>
  body,#map{margin:0;height:100vh;background:#0a0f1e;}
  .leaflet-popup-content{font-family:sans-serif;color:#0a0f1e;}
</style>
</head><body><div id="map"></div>
<script>
var map = L.map('map', { center: [20, 0], zoom: 2, preferCanvas: true });
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
  subdomains: 'abcd', maxZoom: 20
}).addTo(map);
var SEV_COLOR = {
  CRITICAL: '#ef4444', HIGH: '#f97316',
  MEDIUM: '#fbbf24', LOW: '#38bdf8', INFO: '#94a3b8'
};
var markers = __MARKERS__;
var cluster = L.markerClusterGroup({
  chunkedLoading: true,
  showCoverageOnHover: false,
  maxClusterRadius: 45,
  spiderfyOnMaxZoom: true,
});
markers.forEach(function(m) {
  var color = SEV_COLOR[m.sev] || SEV_COLOR.INFO;
  var radius = 4 + Math.min(10, Math.sqrt(m.count));
  var marker = L.circleMarker([m.lat, m.lon], {
    radius: radius,
    color: color,
    weight: 1.2,
    fillColor: color,
    fillOpacity: m.approx ? 0.35 : 0.7,
    dashArray: m.approx ? '2,3' : null,
  }).bindPopup(
    '<b>' + m.flag + ' ' + m.ip + '</b><br>' +
    (m.code ? m.code + ' &middot; ' : '') +
    m.count.toLocaleString() + ' events (24h)<br>' +
    'severity: ' + m.sev +
    (m.approx ? '<br><i>country-level location</i>' : '')
  );
  cluster.addLayer(marker);
});
map.addLayer(cluster);
</script></body></html>""".replace("__MARKERS__", markers_json)
        GLib.idle_add(self._webview.load_html, html, "about:blank")
