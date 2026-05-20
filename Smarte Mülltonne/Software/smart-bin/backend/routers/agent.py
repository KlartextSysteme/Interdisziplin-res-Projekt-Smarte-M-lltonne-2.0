"""Server-Sent Events endpoint for the LangChain agent.

Event types streamed to the client:
- `token`:        { content: str }                         ← partial text from assistant
- `tool_call`:    { tool: str, input: dict }               ← agent invokes a tool
- `tool_result`:  { tool: str, output: str }               ← tool returned
- `done`:         {}                                        ← end of turn
- `error`:        { message: str }                          ← agent failed
"""
import json
import logging
from typing import AsyncIterator, Literal

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import AIMessage, HumanMessage

from agent.planner import get_agent

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatHistoryItem] | None = None


def _sse(event: str, data: dict) -> str:
    """Format a single Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _history_to_messages(history: list[ChatHistoryItem] | None):
    if not history:
        return []
    return [
        HumanMessage(content=h.content) if h.role == "user" else AIMessage(content=h.content)
        for h in history
    ]


async def _stream(payload: ChatRequest) -> AsyncIterator[str]:
    try:
        executor = get_agent()
    except Exception as e:
        logger.exception("agent init failed")
        yield _sse("error", {"message": f"Agent-Initialisierung fehlgeschlagen: {e}"})
        return

    messages = _history_to_messages(payload.history)
    messages.append(HumanMessage(content=payload.message))

    try:
        async for event in executor.astream_events(
            {"messages": messages},
            version="v2",
        ):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk is None:
                    continue
                # Claude returns content as list of blocks or str
                content = chunk.content
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = block.get("text", "")
                            if text:
                                yield _sse("token", {"content": text})
                elif isinstance(content, str) and content:
                    yield _sse("token", {"content": content})

            elif kind == "on_tool_start":
                yield _sse(
                    "tool_call",
                    {"tool": event.get("name"), "input": event["data"].get("input", {})},
                )

            elif kind == "on_tool_end":
                output = event["data"].get("output")
                yield _sse(
                    "tool_result",
                    {"tool": event.get("name"), "output": str(output) if output is not None else ""},
                )

        yield _sse("done", {})

    except Exception as e:
        logger.exception("agent stream failed")
        yield _sse("error", {"message": str(e)})


@router.post("/chat")
async def chat(payload: ChatRequest):
    return StreamingResponse(
        _stream(payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",   # disable proxy buffering
        },
    )
