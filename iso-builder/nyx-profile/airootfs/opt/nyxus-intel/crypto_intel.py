# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
NYXUS INTEL · crypto_intel.py
Cryptocurrency address investigation.

  • BTC  → blockchain.info public REST (no key)
  • ETH  → Etherscan V2 unified API (key required, free tier OK)
            All chains share api.etherscan.io/v2/api with chainid=1 (mainnet)

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

from typing import Dict, Any, Optional

import requests

# ── NYXUS palette (single source of truth · rev r13) ────────────────
try:
    from nyxus_palette import (
        WHITE_PURE, WHITE_OFF, GREY_LIGHT, GREY_MID, GREY_TERTIARY,
        INK_FADED, INK_BLACK,
        GLASS_DARK, GLASS_DEEPER, GLASS_DEEPEST,
        HAIRLINE_WHITE, HAIRLINE_INK,
        SHADOW_INK_ACTIVE, SHADOW_INK_INACTIVE,
        RADIUS_CARD, RADIUS_PILL, RADIUS_INPUT,
        FONT_UI, FONT_MONO, FONT_DISPLAY,
        format_css, assert_no_forbidden,
    )
except Exception:
    # palette module is shipped alongside every NYXUS app via
    # nyxus_install.sh; if it's missing, fall back to literals so
    # the app still launches.
    WHITE_PURE='#ffffff'; WHITE_OFF='#e8edf5'; GREY_LIGHT='#c8ccd6'
    GREY_MID='#9aa0ad'; GREY_TERTIARY='#6a6e78'
    INK_FADED='#0a0a0a'; INK_BLACK='#000000'
    GLASS_DARK='rgba(8, 12, 20, 0.55)'
    GLASS_DEEPER='rgba(15, 20, 32, 0.72)'
    GLASS_DEEPEST='rgba(5, 7, 12, 0.92)'
    HAIRLINE_WHITE='rgba(255, 255, 255, 0.10)'
    HAIRLINE_INK='rgba(0, 0, 0, 0.45)'
    SHADOW_INK_ACTIVE='rgba(0, 0, 0, 0.65)'
    SHADOW_INK_INACTIVE='rgba(0, 0, 0, 0.20)'
    RADIUS_CARD=14; RADIUS_PILL=12; RADIUS_INPUT=10
    FONT_UI='Inter'; FONT_MONO='JetBrains Mono'; FONT_DISPLAY='Inter Display'
    def format_css(t):
        _d = {
            'WHITE_PURE': WHITE_PURE, 'WHITE_OFF': WHITE_OFF,
            'GREY_LIGHT': GREY_LIGHT, 'GREY_MID': GREY_MID,
            'GREY_TERTIARY': GREY_TERTIARY,
            'INK_FADED': INK_FADED, 'INK_BLACK': INK_BLACK,
            'GLASS_DARK': GLASS_DARK, 'GLASS_DEEPER': GLASS_DEEPER,
            'GLASS_DEEPEST': GLASS_DEEPEST,
            'HAIRLINE_WHITE': HAIRLINE_WHITE, 'HAIRLINE_INK': HAIRLINE_INK,
            'SHADOW_INK_ACTIVE': SHADOW_INK_ACTIVE,
            'SHADOW_INK_INACTIVE': SHADOW_INK_INACTIVE,
            'RADIUS_CARD': RADIUS_CARD, 'RADIUS_PILL': RADIUS_PILL,
            'RADIUS_INPUT': RADIUS_INPUT,
            'FONT_UI': FONT_UI, 'FONT_MONO': FONT_MONO,
            'FONT_DISPLAY': FONT_DISPLAY,
        }
        return t.format_map(_d)
    def assert_no_forbidden(*a, **k): pass
# ─────────────────────────────────────────────────────────────────────


UA = "NYXUS-INTEL/1.0 (research/OSINT)"
TIMEOUT = 25


def _err(msg): return {"__error__": msg}


def btc_address(address: str) -> Dict[str, Any]:
    r = requests.get(f"https://blockchain.info/rawaddr/{address}",
                     params={"limit": 50},
                     timeout=TIMEOUT, headers={"User-Agent": UA})
    if r.status_code == 404:
        return {"address": address, "found": False}
    if r.status_code != 200:
        return _err(f"blockchain.info HTTP {r.status_code}")
    d = r.json()

    txs = []
    for tx in (d.get("txs") or [])[:25]:
        txs.append({
            "hash":         tx.get("hash"),
            "time":         tx.get("time"),
            "size":         tx.get("size"),
            "result":       tx.get("result"),
            "fee":          tx.get("fee"),
            "block_height": tx.get("block_height"),
            "n_inputs":     len(tx.get("inputs") or []),
            "n_outputs":    len(tx.get("out") or []),
        })

    return {
        "address":            d.get("address"),
        "found":              True,
        "n_tx":               d.get("n_tx"),
        "total_received_sat": d.get("total_received"),
        "total_sent_sat":     d.get("total_sent"),
        "balance_sat":        d.get("final_balance"),
        "balance_btc":        (d.get("final_balance") or 0) / 1e8,
        "received_btc":       (d.get("total_received") or 0) / 1e8,
        "sent_btc":           (d.get("total_sent") or 0) / 1e8,
        "first_seen":         (d.get("txs") or [{}])[-1].get("time")
                              if d.get("txs") else None,
        "transactions":       txs,
        "explorer":           f"https://www.blockchain.com/btc/address/{address}",
    }


# ── Etherscan V2 unified endpoint ────────────────────────────────────────
ETHERSCAN_V2 = "https://api.etherscan.io/v2/api"


def _es_v2(params: Dict[str, Any], key: str) -> Dict[str, Any]:
    p = {"chainid": 1, "apikey": key, **params}
    r = requests.get(ETHERSCAN_V2, params=p,
                     timeout=TIMEOUT, headers={"User-Agent": UA})
    return {"_status": r.status_code, "_json":
            (r.json() if r.headers.get("Content-Type", "").startswith("application/json")
             else {"status": "0", "message": r.text[:200]})}


def eth_address(address: str, key: Optional[str]) -> Dict[str, Any]:
    if not key:
        return _err("set Etherscan API key in Settings (free at etherscan.io/myapikey)")

    # 1. Balance
    rb = _es_v2({"module": "account", "action": "balance",
                 "address": address, "tag": "latest"}, key)
    if rb["_status"] != 200:
        return _err(f"Etherscan v2 HTTP {rb['_status']}")
    bd = rb["_json"]
    if str(bd.get("status")) == "0" and (bd.get("message") or "").lower().startswith("notok"):
        return _err(f"Etherscan v2: {bd.get('result') or bd.get('message')}")
    wei = int(bd.get("result") or 0)
    eth = wei / 1e18

    # 2. Recent normal txs
    rt = _es_v2({"module": "account", "action": "txlist",
                 "address": address, "startblock": 0, "endblock": 99999999,
                 "page": 1, "offset": 25, "sort": "desc"}, key)
    txs_raw = rt["_json"].get("result") if rt["_status"] == 200 else []
    txs = []
    if isinstance(txs_raw, list):
        for t in txs_raw:
            txs.append({
                "hash":      t.get("hash"),
                "block":     t.get("blockNumber"),
                "time":      int(t.get("timeStamp") or 0),
                "from":      t.get("from"),
                "to":        t.get("to"),
                "value_eth": int(t.get("value") or 0) / 1e18,
                "gas_used":  int(t.get("gasUsed") or 0),
                "is_error":  t.get("isError"),
            })

    # 3. ERC-20 token transfers
    rk = _es_v2({"module": "account", "action": "tokentx",
                 "address": address, "page": 1, "offset": 25, "sort": "desc"}, key)
    tokens = []
    tk_raw = rk["_json"].get("result") if rk["_status"] == 200 else []
    if isinstance(tk_raw, list):
        for t in tk_raw:
            try:
                dec = int(t.get("tokenDecimal") or 0)
                amt = int(t.get("value") or 0) / (10 ** dec) if dec else int(t.get("value") or 0)
            except Exception:
                amt = None
            tokens.append({
                "hash":       t.get("hash"),
                "time":       int(t.get("timeStamp") or 0),
                "from":       t.get("from"),
                "to":         t.get("to"),
                "token":      t.get("tokenSymbol"),
                "token_name": t.get("tokenName"),
                "amount":     amt,
            })

    return {
        "address":         address,
        "balance_wei":     wei,
        "balance_eth":     eth,
        "tx_count":        len(txs),
        "transactions":    txs,
        "token_transfers": tokens,
        "explorer":        f"https://etherscan.io/address/{address}",
        "api":             "Etherscan V2 (chainid=1)",
    }
