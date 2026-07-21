from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from collections import defaultdict
import aiosqlite
from ..database import get_db
from ..models import Run, RunFlag

router = APIRouter(prefix="/api/runs", tags=["runs"])

def row_to_run(row) -> dict:
    return {
        "id": row["id"],
        "toolId": row["tool_id"],
        "toolName": row["tool_name"],
        "command": row["command"],
        "status": row["status"],
        "output": row["output"],
        "startedAt": row["started_at"],
        "endedAt": row["ended_at"],
        "isFlagged": bool(row["is_flagged"]),
        "flagNote": row["flag_note"],
        "severity": row["severity"],
    }

@router.get("/library")
async def get_command_library(db: aiosqlite.Connection = Depends(get_db)):
    """Return all executed commands grouped by category and tool for study."""
    from ..tools_data import TOOLS
    tool_map = {t["id"]: t for t in TOOLS}

    async with db.execute(
        "SELECT tool_id, tool_name, command, status, output, started_at FROM runs ORDER BY started_at DESC"
    ) as cur:
        rows = await cur.fetchall()

    if not rows:
        return []

    # Group: category -> tool_id -> [runs]
    cat_tools: dict = defaultdict(lambda: defaultdict(list))
    for row in rows:
        tool_id = row["tool_id"]
        tool_info = tool_map.get(tool_id, {"category": "Uncategorized", "difficulty": ""})
        category = tool_info.get("category", "Uncategorized")
        cat_tools[category][tool_id].append(dict(row))

    result = []
    for category in sorted(cat_tools.keys()):
        tools_in_cat = cat_tools[category]
        tool_entries = []
        for tool_id, tool_runs in tools_in_cat.items():
            tool_info = tool_map.get(tool_id, {})
            # Group unique commands
            cmd_groups: dict = defaultdict(list)
            for run in tool_runs:
                cmd_groups[run["command"]].append(run)

            unique_commands = []
            for cmd, cmd_runs in cmd_groups.items():
                successful = [r for r in cmd_runs if r["status"] == "completed"]
                latest = cmd_runs[0]
                unique_commands.append({
                    "command": cmd,
                    "runCount": len(cmd_runs),
                    "successCount": len(successful),
                    "lastRun": latest["started_at"],
                    "lastStatus": latest["status"],
                    "lastOutput": latest["output"] or "",
                })
            # Sort by most recently run
            unique_commands.sort(key=lambda x: x["lastRun"], reverse=True)

            tool_entries.append({
                "toolId": tool_id,
                "toolName": tool_runs[0]["tool_name"],
                "difficulty": tool_info.get("difficulty", ""),
                "runCount": len(tool_runs),
                "lastRun": tool_runs[0]["started_at"],
                "commands": unique_commands,
            })

        tool_entries.sort(key=lambda x: x["lastRun"], reverse=True)
        result.append({
            "category": category,
            "totalRuns": sum(t["runCount"] for t in tool_entries),
            "tools": tool_entries,
        })

    return result


@router.get("", response_model=List[Run])
async def list_runs(
    toolId: Optional[str] = Query(None),
    limit: Optional[int] = Query(50),
    offset: Optional[int] = Query(0),
    db: aiosqlite.Connection = Depends(get_db),
):
    if toolId:
        async with db.execute(
            "SELECT * FROM runs WHERE tool_id = ? ORDER BY started_at DESC LIMIT ? OFFSET ?",
            (toolId, limit, offset),
        ) as cur:
            rows = await cur.fetchall()
    else:
        async with db.execute(
            "SELECT * FROM runs ORDER BY started_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ) as cur:
            rows = await cur.fetchall()
    return [row_to_run(r) for r in rows]

@router.get("/{run_id}", response_model=Run)
async def get_run(run_id: int, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    return row_to_run(row)

@router.delete("/{run_id}", status_code=204)
async def delete_run(run_id: int, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT id FROM runs WHERE id = ?", (run_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    await db.execute("DELETE FROM runs WHERE id = ?", (run_id,))
    await db.commit()

@router.post("/{run_id}/flag", response_model=Run)
async def flag_run(run_id: int, body: RunFlag, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    await db.execute(
        "UPDATE runs SET is_flagged = ?, flag_note = ?, severity = ? WHERE id = ?",
        (1 if body.flagged else 0, body.flagNote, body.severity, run_id),
    )
    await db.commit()
    async with db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)) as cur:
        updated = await cur.fetchone()
    return row_to_run(updated)
