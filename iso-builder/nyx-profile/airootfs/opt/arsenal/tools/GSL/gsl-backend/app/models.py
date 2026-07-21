from pydantic import BaseModel
from typing import Optional, List

class ToolParam(BaseModel):
    name: str
    label: str
    type: str
    defaultValue: str
    placeholder: Optional[str] = None
    required: bool = False

class Tool(BaseModel):
    id: str
    name: str
    description: str
    category: str
    difficulty: str
    estimatedTime: str
    command: str
    params: List[ToolParam] = []
    learnContent: Optional[str] = None
    isFavorite: bool = False
    tags: List[str] = []

class FavoriteToggle(BaseModel):
    favorite: bool

class Run(BaseModel):
    id: int
    toolId: str
    toolName: str
    command: str
    status: str
    output: Optional[str] = None
    startedAt: str
    endedAt: Optional[str] = None
    isFlagged: bool = False
    flagNote: Optional[str] = None
    severity: Optional[str] = None

class RunFlag(BaseModel):
    flagged: bool
    flagNote: Optional[str] = None
    severity: Optional[str] = None

class Note(BaseModel):
    id: int
    toolId: Optional[str] = None
    runId: Optional[int] = None
    content: str
    title: Optional[str] = None
    createdAt: str
    updatedAt: str

class NoteInput(BaseModel):
    content: str
    title: Optional[str] = None
    toolId: Optional[str] = None
    runId: Optional[int] = None

class NoteUpdate(BaseModel):
    content: Optional[str] = None
    title: Optional[str] = None

class DashboardSummary(BaseModel):
    totalTools: int
    totalRuns: int
    totalCategories: int
    favoriteCount: int
    findingsCount: int
    recentActivity: str

class NetworkDevice(BaseModel):
    ip: str
    hostname: Optional[str] = None
    mac: Optional[str] = None
    vendor: Optional[str] = None
    status: str

class ExecuteRequest(BaseModel):
    toolId: str
    params: dict
    command: str  # the full resolved command to execute
