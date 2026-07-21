from fastapi import APIRouter, Depends, HTTPException
from typing import List
import aiosqlite
from ..database import get_db
from ..models import Note, NoteInput, NoteUpdate

router = APIRouter(prefix="/api/notes", tags=["notes"])

def row_to_note(row) -> dict:
    return {
        "id": row["id"],
        "toolId": row["tool_id"],
        "runId": row["run_id"],
        "content": row["content"],
        "title": row["title"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }

@router.get("", response_model=List[Note])
async def list_notes(db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT * FROM notes ORDER BY created_at DESC") as cur:
        rows = await cur.fetchall()
    return [row_to_note(r) for r in rows]

@router.post("", response_model=Note, status_code=201)
async def create_note(body: NoteInput, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute(
        "INSERT INTO notes (tool_id, run_id, content, title) VALUES (?, ?, ?, ?)",
        (body.toolId, body.runId, body.content, body.title),
    ) as cur:
        note_id = cur.lastrowid
    await db.commit()
    async with db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)) as cur:
        row = await cur.fetchone()
    return row_to_note(row)

@router.patch("/{note_id}", response_model=Note)
async def update_note(note_id: int, body: NoteUpdate, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Note not found")

    updates = []
    values = []
    if body.content is not None:
        updates.append("content = ?")
        values.append(body.content)
    if body.title is not None:
        updates.append("title = ?")
        values.append(body.title)
    updates.append("updated_at = datetime('now')")
    values.append(note_id)

    await db.execute(f"UPDATE notes SET {', '.join(updates)} WHERE id = ?", values)
    await db.commit()
    async with db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)) as cur:
        updated = await cur.fetchone()
    return row_to_note(updated)

@router.delete("/{note_id}", status_code=204)
async def delete_note(note_id: int, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT id FROM notes WHERE id = ?", (note_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Note not found")
    await db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    await db.commit()
