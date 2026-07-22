import asyncio
import subprocess
import shlex
from datetime import datetime, timezone
from typing import Dict
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.websockets import WebSocketState
import aiosqlite
from .. import auth
from ..database import DB_PATH
from ..models import ExecuteRequest
from ..tools_data import TOOLS_BY_ID

router = APIRouter(tags=["execute"])

# NOTE (scope): this is a real one-shot command runner — it spawns the process,
# streams stdout, and exits. It is intentionally NOT an interactive PTY (no stdin
# over the socket). Access is gated by auth and scoped to local/isolated-lab use.
# TODO(optional-hardening): if exposing beyond a trusted single user, add a
#   command/tool allow-list here (e.g. restrict argv[0] to TOOLS_BY_ID commands).
# TODO(optional): add a true interactive terminal via pty/ptyprocess + stdin.

# Track active processes by run_id
active_processes: Dict[int, subprocess.Popen] = {}

@router.post("/api/execute", status_code=201, dependencies=[Depends(auth.require_auth)])
async def start_execution(body: ExecuteRequest):
    """Create a run record and return the run_id for WebSocket connection."""
    tool = TOOLS_BY_ID.get(body.toolId)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        async with db.execute(
            "INSERT INTO runs (tool_id, tool_name, command, status, started_at) VALUES (?, ?, ?, 'pending', ?)",
            (body.toolId, tool["name"], body.command, datetime.now(timezone.utc).isoformat()),
        ) as cur:
            run_id = cur.lastrowid
        await db.commit()
    finally:
        await db.close()

    return {"runId": run_id}

@router.post("/api/runs/{run_id}/kill", dependencies=[Depends(auth.require_auth)])
async def kill_run(run_id: int):
    """Kill a running process."""
    proc = active_processes.get(run_id)
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        return {"killed": True}
    return {"killed": False, "message": "Process not found or already finished"}

@router.websocket("/ws/run/{run_id}")
async def run_tool_ws(websocket: WebSocket, run_id: int):
    """
    WebSocket endpoint that:
    1. Waits for the client to send the command to execute
    2. Spawns the real subprocess
    3. Streams stdout/stderr line by line back to the client
    4. Saves full output to the DB when done
    """
    # Authenticate BEFORE accepting/streaming — the socket runs arbitrary
    # commands, so an unauthenticated client must never reach the runner.
    if not await auth.require_ws_auth(websocket):
        return
    await websocket.accept()

    # Wait for the command message from the client
    try:
        data = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
    except (asyncio.TimeoutError, Exception):
        await websocket.close()
        return

    command = data.get("command", "")
    if not command:
        await websocket.send_json({"type": "error", "line": "No command provided"})
        await websocket.close()
        return

    # Update run status to running
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        await db.execute("UPDATE runs SET status = 'running' WHERE id = ?", (run_id,))
        await db.commit()
    finally:
        await db.close()

    output_lines = []
    exit_code = None

    try:
        # Parse command safely
        try:
            cmd_parts = shlex.split(command)
        except ValueError:
            cmd_parts = command.split()

        proc = subprocess.Popen(
            cmd_parts,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        active_processes[run_id] = proc

        # Stream output line by line
        while True:
            # Check if client disconnected
            if websocket.client_state == WebSocketState.DISCONNECTED:
                proc.terminate()
                break

            line = await asyncio.get_event_loop().run_in_executor(None, proc.stdout.readline)
            if not line:
                break
            line = line.rstrip("\n")
            output_lines.append(line)
            try:
                await websocket.send_json({"type": "output", "line": line})
            except Exception:
                proc.terminate()
                break

        proc.wait(timeout=5)
        exit_code = proc.returncode

    except FileNotFoundError as e:
        err = f"Command not found: {cmd_parts[0] if cmd_parts else command}. Is it installed?"
        output_lines.append(err)
        try:
            await websocket.send_json({"type": "error", "line": err})
        except Exception:
            pass
        exit_code = 127
    except Exception as e:
        err = f"Execution error: {str(e)}"
        output_lines.append(err)
        try:
            await websocket.send_json({"type": "error", "line": err})
        except Exception:
            pass
        exit_code = 1
    finally:
        active_processes.pop(run_id, None)

    # Save output and mark complete
    full_output = "\n".join(output_lines)
    status = "completed" if exit_code == 0 else ("killed" if exit_code == -15 else "error")
    ended_at = datetime.now(timezone.utc).isoformat()

    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        await db.execute(
            "UPDATE runs SET status = ?, output = ?, ended_at = ? WHERE id = ?",
            (status, full_output, ended_at, run_id),
        )
        await db.commit()
    finally:
        await db.close()

    # Send completion message
    try:
        await websocket.send_json({
            "type": "done",
            "exitCode": exit_code,
            "status": status,
        })
        await websocket.close()
    except Exception:
        pass
