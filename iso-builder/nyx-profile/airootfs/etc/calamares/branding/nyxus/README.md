# NYXUS Calamares branding

This directory holds the NYXUS-branded assets used by the Calamares
installer (`/etc/calamares/branding/nyxus/`).

Required image assets (provide via `nyxus-build-iso.sh` before
`mkarchiso`):

| File          | Purpose                                  | Recommended size |
|---------------|------------------------------------------|------------------|
| `logo.png`    | Sidebar + window icon                    | 256×256 PNG      |
| `welcome.png` | Hero image on the welcome screen         | 800×400 PNG      |

`show.qml` is the slideshow and ships in this repo. `branding.desc`
references everything by relative path.
