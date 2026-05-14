// ~/.mozilla/firefox/nyxus.default/user.js
// NYXUS Sprint K-D rev r16 — Firefox per-profile prefs (locked 2026-05-14)
//
// Every preference here is a hard requirement of the rev r16 brand
// contract OR a UX baseline so a freshly-spawned Firefox feels like a
// native NYXUS app. user.js is read on every Firefox start and the
// values are written into prefs.js at runtime — the user can still
// override them in about:config but they reset on next launch.

// ── REQUIRED for userChrome.css / userContent.css to load at all ─────
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);

// ── Force the chrome into dark theme (matches userChrome palette) ────
user_pref("ui.systemUsesDarkTheme", 1);
user_pref("layout.css.prefers-color-scheme.content-override", 0);
user_pref("browser.theme.toolbar-theme", 0);   // 0 = dark
user_pref("browser.theme.content-theme",  0);  // 0 = dark
user_pref("browser.in-content.dark-mode", true);
user_pref("widget.gtk.theme-scrollbar-colors.enabled", false);

// ── Wayland-native rendering so Hyprland sees a real surface ─────────
user_pref("widget.wayland.opaque-region.enabled",  false);
user_pref("widget.wayland.fractional-scale.enabled", true);
user_pref("gfx.webrender.all", true);
user_pref("media.ffmpeg.vaapi.enabled", true);

// ── New-tab page → simple, no Pocket / sponsored content / promos ────
user_pref("browser.newtabpage.activity-stream.feeds.section.topstories", false);
user_pref("browser.newtabpage.activity-stream.feeds.topsites",          true);
user_pref("browser.newtabpage.activity-stream.showSponsored",           false);
user_pref("browser.newtabpage.activity-stream.showSponsoredTopSites",   false);
user_pref("browser.newtabpage.activity-stream.feeds.snippets",          false);
user_pref("browser.newtabpage.activity-stream.feeds.discoverystreamfeed", false);
user_pref("browser.newtabpage.activity-stream.feeds.section.highlights", false);
user_pref("browser.newtabpage.activity-stream.section.highlights.includePocket", false);
user_pref("browser.newtabpage.activity-stream.improvesearch.topSiteSearchShortcuts", false);

// ── Telemetry off (locked NYXUS privacy default — same as Privacy page) ─
user_pref("toolkit.telemetry.enabled",          false);
user_pref("toolkit.telemetry.unified",          false);
user_pref("toolkit.telemetry.archive.enabled",  false);
user_pref("toolkit.telemetry.bhrPing.enabled",  false);
user_pref("toolkit.telemetry.firstShutdownPing.enabled", false);
user_pref("toolkit.telemetry.newProfilePing.enabled",    false);
user_pref("toolkit.telemetry.shutdownPingSender.enabled", false);
user_pref("toolkit.telemetry.updatePing.enabled", false);
user_pref("datareporting.policy.dataSubmissionEnabled",  false);
user_pref("datareporting.healthreport.uploadEnabled",    false);
user_pref("app.shield.optoutstudies.enabled",            false);
user_pref("browser.crashReports.unsubmittedCheck.autoSubmit2", false);

// ── Pocket integration off (we do not ship Pocket as a feature) ──────
user_pref("extensions.pocket.enabled", false);

// ── Suppress first-run / what's-new tabs so the install feels clean ──
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("browser.aboutwelcome.enabled", false);
user_pref("startup.homepage_welcome_url", "about:home");
user_pref("startup.homepage_welcome_url.additional", "");
user_pref("browser.disableResetPrompt", true);
user_pref("browser.shell.checkDefaultBrowser", false);

// ── Compact density (slim tabs as required by the sprint brief) ──────
user_pref("browser.uidensity", 1);            // 0=normal, 1=compact, 2=touch
user_pref("browser.compactmode.show", true);

// ── Tabs above url bar; show bookmark bar; hairline title-bar off ────
user_pref("browser.tabs.inTitlebar", 1);
user_pref("browser.toolbars.bookmarks.visibility", "always");

// ── Dark scrollbars ──────────────────────────────────────────────────
user_pref("widget.non-native-theme.scrollbar.style", 4);
