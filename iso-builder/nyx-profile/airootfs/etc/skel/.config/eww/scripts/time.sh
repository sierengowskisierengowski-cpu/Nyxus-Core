#!/usr/bin/env bash
# NYXUS clock poll for eww TIME variable (JSON)
# 12-hour format (owner request 2026-07-27). %-I drops the leading zero so
# the string never gets WIDER than the old 24h "00:46" and the bar clock
# slots keep their measured widths - see the bar-width notes in eww.scss.
# `ampm` is a separate field so widgets can show AM/PM without re-padding.
date +'{"hms":"%-I:%M:%S","hm":"%-I:%M","sec":"%S","ampm":"%p","date":"%a %d %b","long":"%A, %B %d %Y"}'
