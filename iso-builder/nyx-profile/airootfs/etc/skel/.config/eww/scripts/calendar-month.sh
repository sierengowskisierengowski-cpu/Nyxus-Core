#!/usr/bin/env bash
# NYXUS · EWW · calendar grid (full month with day-of-week + today flag)
# Emits {month, year, today, weeks:[[{d,today,inmonth},...x7],...]}
set -u

today_ymd=$(date +'%Y-%m-%d')
month_name=$(date +'%B')
year=$(date +'%Y')
today_d=$(date +'%-d')

# First weekday (0=Sun..6=Sat) of the month and number of days in the month
first_dow=$(date -d "$(date +%Y-%m-01)" +%w)
days_in_month=$(date -d "$(date +%Y-%m-01) +1 month -1 day" +%-d)

# Build a flat day list: leading blanks + days + trailing blanks to fill 6*7
weeks_json=""
day=1
total_cells=42  # 6 weeks
filled=0
week=""
cell_in_week=0

emit_cell() {
  # $1 = label  $2 = today(true|false)  $3 = inmonth(true|false)
  week+="$(printf '{"d":"%s","today":%s,"inmonth":%s}' "$1" "$2" "$3"),"
  cell_in_week=$((cell_in_week + 1))
  if (( cell_in_week == 7 )); then
    week="${week%,}"
    weeks_json+="[$week],"
    week=""
    cell_in_week=0
  fi
}

# Leading blanks (previous month)
for ((i=0; i<first_dow; i++)); do emit_cell "" false false; done

# In-month days
for ((d=1; d<=days_in_month; d++)); do
  if (( d == today_d )); then emit_cell "$d" true true
  else                        emit_cell "$d" false true
  fi
done

# Trailing blanks
filled=$((first_dow + days_in_month))
trailing=$((total_cells - filled))
for ((i=0; i<trailing; i++)); do emit_cell "" false false; done

weeks_json="${weeks_json%,}"

if command -v jq >/dev/null 2>&1; then
  jq -nc --arg month "$month_name" --arg year "$year" --arg today "$today_ymd" \
         --argjson weeks "[$weeks_json]" \
    '{month:$month, year:$year, today:$today, weeks:$weeks}'
else
  printf '{"month":"%s","year":"%s","today":"%s","weeks":[%s]}\n' \
    "$month_name" "$year" "$today_ymd" "$weeks_json"
fi
