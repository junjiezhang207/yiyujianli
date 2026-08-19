"""SSE Stream request/response models.

This module defines the data models for SSE streaming API.
"""

from datetime import datetime
from typing import Any, Optional
import uuid

from pydantic import BaseModel, Field


class StreamRequest(BaseModel):
    """SSE stream request model."""

    prompt: Optional[str] = Field(None, description="User message to send to the agent")
    message: Optional[str] = Field(None, description="Alias for prompt")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    resume_path: Optional[str] = Field(None, description="Path to resume file")
    resume_data: Optional[dict] = Field(None, description="Resume data payload")
    model: Optional[str] = Field(None, description="LLM model override")
    agent_runtime: Optional[str] = Field(None, description="Agent runtime override, e.g. langchain_v1")
    use_langchain_v1: Optional[bool] = Field(None, description="Use the LangChain 1.x runtime for this request")
    run_id: Optional[str] = Field(None, description="Client run ID for this request")
    cursor: Optional[str] = Field(None, description="Cursor for resume/reconnect")
    resume: Optional[bool] = Field(False, description="Whether this is a resume request")


class SSEEvent(BaseModel):
    """SSE event model for responses."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    data: Any = None
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_sse_format(self) -> str:
        """Convert event to SSE format string."""
        import json

        event_dict = {
            "id": self.id,
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }
        return f"id: {self.id}\ndata: {json.dumps(event_dict, ensure_ascii=False)}\n\n"


class HeartbeatEvent(BaseModel):
    """Heartbeat event for keeping SSE connection alive."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "heartbeat"
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_sse_format(self) -> str:
        """Convert heartbeat event to SSE format string."""
        import json

        event_dict = {
            "id": self.id,
            "type": self.type,
            "timestamp": self.timestamp.isoformat(),
        }
        return f"id: {self.id}\ndata: {json.dumps(event_dict, ensure_ascii=False)}\n\n"
