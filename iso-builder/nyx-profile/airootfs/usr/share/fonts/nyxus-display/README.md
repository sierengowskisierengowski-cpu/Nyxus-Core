NYXUS Display Fonts
===================

This directory contains the NYXUS-bundled display fonts used by the
brand contract (rev r15):

  * **Caveat** (handwritten accent, OFL) — drop the OFL build of the
    Caveat family here as `Caveat-Regular.ttf`, `Caveat-Medium.ttf`,
    `Caveat-SemiBold.ttf`, and `Caveat-Bold.ttf`.
    Source: https://fonts.google.com/specimen/Caveat (SIL OFL 1.1)

The build host is responsible for placing the font binaries in this
directory before `mkarchiso` runs. `verify-profile.sh` section 13v
checks that at least `Caveat-Regular.ttf` is present.

Inter and JetBrains Mono Nerd Font are installed via pacman packages
(`inter-font`, `ttf-jetbrains-mono-nerd`) and do not need to be
bundled here.

Fontconfig will pick fonts up automatically once they're placed in
this directory at install time.
