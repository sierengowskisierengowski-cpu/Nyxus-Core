from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
import aiosqlite
import re
from pydantic import BaseModel
from ..database import get_db
from ..models import Tool, ToolParam, FavoriteToggle
from ..tools_data import TOOLS, TOOLS_BY_ID, CATEGORIES

router = APIRouter(prefix="/api/tools", tags=["tools"])

async def get_favorites(db: aiosqlite.Connection) -> set:
    async with db.execute("SELECT tool_id FROM tool_favorites WHERE is_favorite = 1") as cur:
        rows = await cur.fetchall()
    return {row["tool_id"] for row in rows}

def build_tool(data: dict, favorites: set) -> dict:
    return {
        **{k: v for k, v in data.items() if k != "commandTemplate"},
        "isFavorite": data["id"] in favorites,
        "params": data.get("params", []),
    }

@router.get("", response_model=List[Tool])
async def list_tools(
    category: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: aiosqlite.Connection = Depends(get_db),
):
    favorites = await get_favorites(db)
    results = TOOLS

    if category:
        results = [t for t in results if t["category"].lower() == category.lower()]
    if difficulty:
        results = [t for t in results if t["difficulty"].lower() == difficulty.lower()]
    if search:
        q = search.lower()
        results = [t for t in results if q in t["name"].lower() or q in t["description"].lower() or any(q in tag for tag in t.get("tags", []))]

    return [build_tool(t, favorites) for t in results]

@router.get("/{tool_id}", response_model=Tool)
async def get_tool(tool_id: str, db: aiosqlite.Connection = Depends(get_db)):
    tool = TOOLS_BY_ID.get(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    favorites = await get_favorites(db)
    return build_tool(tool, favorites)

class PreviewCommandRequest(BaseModel):
    params: dict = {}

class PreviewCommandResponse(BaseModel):
    command: str

@router.post("/{tool_id}/preview-command", response_model=PreviewCommandResponse)
async def preview_command(tool_id: str, body: PreviewCommandRequest):
    """Resolve a tool's commandTemplate with the given params and return the full command string."""
    tool = TOOLS_BY_ID.get(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    template = tool.get("commandTemplate", tool["command"])
    params = body.params or {}

    # Fill in each {placeholder} from params; leave empty ones blank and strip double spaces
    def replace_placeholder(m):
        key = m.group(1)
        val = params.get(key, "")
        return str(val) if val else ""

    command = re.sub(r'\{(\w+)\}', replace_placeholder, template)
    # Collapse multiple spaces and strip trailing spaces
    command = re.sub(r' {2,}', ' ', command).strip()
    return {"command": command}

@router.post("/{tool_id}/favorites", response_model=Tool)
async def toggle_favorite(
    tool_id: str,
    body: FavoriteToggle,
    db: aiosqlite.Connection = Depends(get_db),
):
    tool = TOOLS_BY_ID.get(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    await db.execute(
        "INSERT INTO tool_favorites (tool_id, is_favorite) VALUES (?, ?) ON CONFLICT(tool_id) DO UPDATE SET is_favorite = excluded.is_favorite",
        (tool_id, 1 if body.favorite else 0),
    )
    await db.commit()

    favorites = await get_favorites(db)
    return build_tool(tool, favorites)
