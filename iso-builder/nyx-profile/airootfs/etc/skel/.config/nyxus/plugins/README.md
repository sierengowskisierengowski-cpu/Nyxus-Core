# NYXUS Bar Plugins

Drop a plugin folder here:

```
~/.config/nyxus/plugins/<your-plugin>/
├── manifest.json
├── widget.yuck     (Eww widget definition — exposes one widget)
├── widget.scss     (Optional — appended to the live theme)
└── poll.sh         (Optional — script polled per manifest.poll_seconds)
```

`manifest.json` schema:

```json
{
  "id":            "weather",
  "name":          "Weather",
  "version":       "1.0.0",
  "author":        "you@example.com",
  "widget":        "weather_widget",
  "slot":          "right",
  "poll_seconds":  60,
  "permissions":   ["network"]
}
```

The loader at `/usr/local/bin/nyxus-bar-plugins` discovers everything in
`~/.config/nyxus/plugins/` and `/usr/share/nyxus/plugins/`, splices the
widget definitions into Eww, and starts the poll scripts under the
user's systemd as `nyxus-plugin@<id>.service`. Slots: `left`, `center`,
`right`. Plugins are sandboxed only by your own UID — review code
before dropping it in.

To uninstall: delete the plugin folder and run `nyxus plugins reload`.
