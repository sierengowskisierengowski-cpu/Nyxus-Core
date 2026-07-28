# NYXUS — Project Inventory & Consolidation Map (2026-07-28)

> **Advisory only.** Nothing here was deleted, moved, or renamed. This is a
> cross-reference of every GitHub repo (47) and local project against what the
> NYXUS build actually ships, to answer: what belongs on the build, what is the
> same thing renamed during iteration, what is unfinished-but-worth-keeping, and
> what might be missing. Owner decides what to act on.
>
> Sources: `gh repo list` (47 own repos), local `.git` scan of `~/Projects`,
> `~/GowskiNet-Vault`, `~/Arsenal`, `~/BAASIC`, `~`, plus `~/Arsenal/registry.toml`
> (what the desktop wires as tools) and the Nyxus-Core tree.

---

## 1. THE CORE THREE (canonical, keep — these ARE the build)

| Project | GitHub | Local | Role |
|---|---|---|---|
| **Nyxus-Core** | `Nyxus-Core` | `~/Nyxus-Core` | The distro. Everything below is either shipped by it or a lab tool it launches. |
| **kage-ryu** | `kage-ryu` | `~/Projects/arch-custom-kernel/linux-kage-ryu` | Custom kernel, baked by default. |
| **Nyxus-Companion-3D** | `Nyxus-Companion-3D` | `~/Nyxus-Core/companion-3d` | Godot 3D companion, nested but its own repo. Not in the ISO. |

---

## 2. ON THE BUILD — lab tools NYXUS actively wires (keep)

These are referenced by `~/Arsenal/registry.toml` and/or the stations, so they
are part of the shipped experience. All have GitHub remotes and local checkouts.

| Tool | GitHub | Local (canonical) | Notes |
|---|---|---|---|
| jeTT | `jeTT` | `~/Projects/jeTT` | AI AV/EDR. Ships (binary staged from live process). Clean. |
| Bifrost | `Bifrost` | `~/Projects/bifrost` | AI EDR, station 9. **58 dirty files locally** — biggest uncommitted drift on the machine. |
| Meli | `Meli` | `~/Projects/meli` | Honeypot command center. |
| honeypot | `honeypot` | `~/Projects/honeypot` | Cowrie/Dionaea/… stack + Meli bridges. |
| Ghost-Relay (c2) | `ghost-relay` | `~/GowskiNet-Vault/Security/ghost-relay` | **`~/Projects/c2` is the SAME repo** (see §4). |
| GSL | `GSL` | `~/GowskiNet-Vault/Security/GSL` | Arsenal web app. |
| RedForge | `RedForge` | `~/GowskiNet-Vault/Security/RedForge` | Arsenal web app (see overlap §4). |
| Forge | `Forge` | `~/GowskiNet-Vault/Security/Forge` | Arsenal web app. |
| CIPHER | `CIPHER` | `~/GowskiNet-Vault/Security/CIPHER` | Arsenal web app. |
| AI-Cyber-Defense-Trainer | `AI-Cyber-Defense-Trainer` | `~/GowskiNet-Vault/AI/AI-Cyber-Defense-Trainer` | Arsenal; GitHub desc calls it "REDFORGE" — overlaps RedForge (§4). |
| Arsenal | `Arsenal` | `~/Arsenal` | The TUI hub that launches the above. Committed into the ISO airootfs. |
| SharkFin NOC (`sharknoc`) | *(unversioned)* | `~/.local/bin/sharknoc` | Repaired + shipped on MESH this session; part of the unversioned shark suite (§5). |

**Registry path drift to fix:** `registry.toml` points "Axiom" at
`~/Projects/axiom` and "Ghost-Relay (c2)" at `~/Projects/c2`, but the *canonical*
git checkouts are elsewhere (`GowskiNet-Vault/Tools/axiom`, `.../Security/ghost-relay`).
The registry uses the remote-less working copies. Not broken, but confusing.

---

## 3. OFF THE BUILD — legitimate standalone projects (keep, not for the ISO)

| Project | GitHub | Local | Why off-build |
|---|---|---|---|
| BAASIC | `BAASIC` | `~/BAASIC` (+ dup, §4) | Media player, Rust. Own product. |
| JuJuWorld | `JuJuWorld` | `~/Projects/JujuWorld/v8e` | Android kids app. Unrelated to the distro. |
| subdue | `subdue` | `~/Projects/subdue` | Rust utility. |
| Helm | `Helm` | `~/GowskiNet-Vault/Network/Helm` | Network control dashboard. Empty-ish locally. |
| Qtile | `Qtile` | `~/GowskiNet-Vault/OS/Qtile` | Alt WM config — superseded by the Hyprland desktop; historical. |
| android-hub | `android-hub` | `~/GowskiNet-Vault/Apps/android-hub` (+ dup, §4) | Android master hub. |
| ghost-relay | `ghost-relay` | (also a lab tool) | Dual-use; listed above. |
| blast-from-the-past | `blast-from-the-past` | *(no local git; retro arcade — see `~/RetroPie`, `~/Emulation`)* | EmulationStation build. Fully separate. |

---

## 4. DUPLICATES & RENAMES — same thing, iterated under another name/path

**These are the "converted to another project" cases the owner asked about.**
None are deleted here; recommendation is which one to treat as canonical.

### 4a. Same repo, checked out twice (pick one working copy)
- **BAASIC**: `~/BAASIC` (clean) **and** `~/Projects/baasic-media-player` (14
  dirty) → both remote `BAASIC`. Two checkouts. Recommend keep `~/BAASIC`,
  archive the Projects copy after saving its 14 uncommitted changes.
- **android-hub**: `~/GowskiNet-Vault/Apps/android-hub` **and**
  `~/GowskiNet-Vault/Apps/Android-Starter-Kit` → both remote `android-hub`.
  "Android-Starter-Kit" is a second checkout, not a separate project.
- **c2 == ghost-relay**: `~/Projects/c2` **and**
  `~/GowskiNet-Vault/Security/ghost-relay` → both remote `ghost-relay`. "c2" is
  the old name; ghost-relay is the current one. The Arsenal registry still
  launches the `~/Projects/c2` copy.

### 4b. axiom — THREE checkouts, one product (real mess)
- `~/Projects/axiom` — git, **no remote** (this is what the registry launches)
- `~/GowskiNet-Vault/Tools/axiom` — remote `axiom` (the canonical GitHub one)
- `~/GowskiNet-Vault/Apps/AXIOM` — git, **no remote**, **19 dirty** (the Electron
  desktop build the session notes say still needs packaging)
Recommend: make `GowskiNet-Vault/Tools/axiom` (the one with a remote) canonical,
fold the useful bits of `Apps/AXIOM` into it, retire `~/Projects/axiom` and point
the registry at the canonical path.

### 4c. AI desktop assistant — FIVE takes on one idea
`HOMOOUSIOS` (Ollama assistant) · `axiom` (native assistant) · `AXIOM` (Electron)
· `Desktop-Assistant-AI` (replit) · `Godsapp`/"GodsApp" (replit). This is the
single biggest "same concept, renamed repeatedly" cluster. **Recommend picking
ONE** to carry forward (axiom is the most developed and is already wired into
Arsenal) and marking the rest as historical. NYXUS also already ships GodsApp as
a carve-out per HANDOFF, so clarify whether GodsApp or axiom is the desktop AI.

### 4d. EDR / XDR — three engines
`jeTT` (Python AI AV/EDR, ships) · `Bifrost` (Python AI EDR, ships, station 9) ·
`Cerberus` (C/eBPF XDR, **GitHub only, no local checkout**). jeTT and Bifrost
already overlap (both were found "running blind" this session). Cerberus is a
third, lower-level take with no local copy. **Recommend**: decide whether
Cerberus's C/eBPF core supersedes or feeds jeTT, or archive it — do not maintain
three parallel EDRs.

### 4e. RedForge vs AI-Cyber-Defense-Trainer
GitHub describes AI-Cyber-Defense-Trainer *as* "GowskiNet REDFORGE (adversary
emulation)", while RedForge is "defender training platform." Adjacent, possibly
a split of one idea. Both ship in Arsenal. Worth confirming they are genuinely
two tools and not one forked in two directions.

---

## 5. SUPERSEDED — the pre-consolidation Nyxus-* micro-repos (archive candidates)

Early NYXUS was ~18 separate GitHub repos, one per component. **All of their
function now lives inside `Nyxus-Core`** (verified: `nyxus_qsd.py`,
`nyxus_hotkeyd.py`, `nyxus_snapd.py`, `nyxus-web` (97 files), `nyxus_notepad.py`,
`nyxus_sysmon`, `nyxus-intel` (34 files) are all tracked in Nyxus-Core). None
have a local checkout — they are GitHub-only remnants.

`Nyxus-API-Server` · `Nyxus-Web` · `Nyxus-Notepad` · `Nyxus-Stickies` ·
`Nyxus-Sysmon` · `Nyxus-Widgets` · `Nyxus-Mockup-Sandbox` · `Nyxus-ISO-Builder` ·
`Nyxus-Scripts` · `Nyxus-Libs` · `Nyxus-Intel` · `Nyxus-Dockd` · `Nyxus-Hotkeyd` ·
`Nyxus-Snapd` · `Nyxus-QSD` · `Nyxus-Wallpaper-Studio` · `Nyxus-Store` ·
`Nyxus-Welcome`

**Recommendation:** these are safe to **archive on GitHub** (not delete) — mark
them archived/read-only so the canonical source is unambiguously Nyxus-Core.
Keep only if a specific one still holds history not copied into Nyxus-Core;
spot-check `Nyxus-Wallpaper-Studio` and `Nyxus-Store` (no obvious Nyxus-Core
equivalent) before archiving those two.

---

## 6. THE SHARK SUITE — unversioned, decide its home

`~/.local/bin` holds **39 `shark*` tools** (sharknoc, sharkctl, sharkalert,
sharkclean, sharkadvisor, sharkchat, …) plus the `sharkdash_*.py` backend — and
**none of it is under version control** (`~/.local/bin` is not a git repo).
Separately:
- `sharkdash` (GitHub `sharkdash`, `~/sharkdash`) — the **btop C++ fork** (branded
  NYXUS work); no built binary.
- `~/.local/build/sharkdash-btop` — the real fork tree (btop v1.4.0 + custom
  pages), also unbuilt.
- `~/sharkdash-fork` — the patch set to reproduce the fork.
- `~/sharkfin-v2` — contains a `sharknoc` binary variant.

**Recommendation:** the shark suite is a real, useful body of work living
entirely outside git. Pick a home for it — either a `sharkfin` GitHub repo or a
directory inside an existing one — and commit `~/.local/bin/shark*` +
`sharkdash_*.py` so it stops being one `rm -rf ~/.local` away from gone. This
session shipped `sharknoc` + its 2 deps into Nyxus-Core as a station tool, but
the other 38 tools remain unversioned.

---

## 7. POSSIBLY MISSING / WORTH ADDING

- **Cerberus** has no local checkout — if its eBPF XDR core is wanted, clone and
  reconcile it with jeTT/Bifrost (§4d).
- **-Insight-Hub** (`-Insight-Hub`, "self-hosted Linux remote control dashboard")
  — no local checkout, and it overlaps `Helm` ("control every device from one
  screen"). Another dedup/decide pair; neither is wired into NYXUS yet, though a
  remote-control panel would fit the security-lab theme.
- **JuJu-s-World** is a *second* Juju repo distinct from `JuJuWorld` — confirm
  which is current (likely another rename pair).
- A **`nyxus-hacker.theme` for btop** (noted in HANDOFF): the terminal monitors
  stay violet/green in hacker mode because btop is a TUI. Small, fits the build.

---

## 8. ONE-LINE VERDICT PER CLUSTER

| Cluster | Verdict |
|---|---|
| Core three (Nyxus-Core / kage-ryu / companion-3d) | **Keep, canonical.** |
| Arsenal lab tools (jeTT, Bifrost, Meli, honeypot, GSL, RedForge, Forge, CIPHER, ACDT, ghost-relay, Arsenal) | **Keep, on-build.** Commit Bifrost's 58 dirty files. |
| axiom ×3 | **Consolidate to one** (Tools/axiom + remote); fix registry path. |
| AI assistant ×5 (HOMOOUSIOS/axiom/AXIOM/Desktop-Assistant-AI/Godsapp) | **Pick one**, archive the rest. |
| EDR ×3 (jeTT/Bifrost/Cerberus) | **Decide the split**; don't run three. |
| Nyxus-* micro-repos ×18 | **Archive on GitHub** — superseded by Nyxus-Core. |
| Duplicate checkouts (BAASIC, android-hub, c2) | **Keep one working copy each.** |
| Shark suite (39 unversioned tools) | **Put under version control before it's lost.** |
| Off-build standalones (JuJuWorld, subdue, Helm, Qtile, blast-from-the-past) | **Keep, separate.** |

*Advisory. No repo was modified by this inventory.*
