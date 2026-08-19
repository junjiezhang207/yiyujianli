from __future__ import annotations

import json
import uuid
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, Field, create_model

from backend.agent.tool.base import BaseTool, ToolResult
from backend.agent.web.streaming.events import ToolCallEvent, ToolResultEvent
from backend.core.logger import get_logger

logger = get_logger(__name__)

EventEmitter = Callable[[Any], Awaitable[None]]


def _json_schema_type_to_python(schema: dict[str, Any]) -> Any:
    if "anyOf" in schema or "oneOf" in schema:
        return Any

    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        non_null = [item for item in schema_type if item != "null"]
        schema_type = non_null[0] if non_null else "string"

    return {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "object": dict[str, Any],
        "array": list[Any],
    }.get(schema_type, Any)


def args_schema_from_openai_schema(tool: BaseTool) -> type[BaseModel]:
    """Build a Pydantic args schema from the project's OpenAI-style tool schema."""
    parameters = tool.parameters or {}
    properties = parameters.get("properties") or {}
    required = set(parameters.get("required") or [])

    fields: dict[str, tuple[Any, Any]] = {}
    for name, prop_schema in properties.items():
        if not isinstance(prop_schema, dict):
            prop_schema = {}
        annotation = _json_schema_type_to_python(prop_schema)
        description = str(prop_schema.get("description") or "")
        default = ... if name in required else None
        fields[name] = (annotation, Field(default, description=description))

    model_name = f"{tool.__class__.__name__}LangChainArgs"
    return create_model(model_name, **fields) if fields else create_model(model_name)


def tool_result_to_text(result: Any) -> str:
    if isinstance(result, ToolResult):
        if result.error:
            return f"Error: {result.error}"
        if result.output is not None:
            return str(result.output)
        if result.structured_data is not None:
            return json.dumps(result.structured_data, ensure_ascii=False)
        if result.system is not None:
            return str(result.system)
        return ""
    if isinstance(result, BaseModel):
        return result.model_dump_json()
    if isinstance(result, (dict, list)):
        return json.dumps(result, ensure_ascii=False)
    return "" if result is None else str(result)


def extract_structured_data(result: Any) -> dict[str, Any] | None:
    if isinstance(result, ToolResult):
        if isinstance(result.structured_data, dict):
            return result.structured_data
        if result.system:
            try:
                parsed = json.loads(result.system)
            except (TypeError, ValueError):
                return None
            return parsed if isinstance(parsed, dict) else None
    return None


def adapt_tool_for_langchain(
    tool: BaseTool,
    *,
    session_id: str,
    emit: EventEmitter,
) -> Any:
    """Wrap an existing project BaseTool as a LangChain 1.x StructuredTool."""
    try:
        from langchain_core.tools import StructuredTool
    except Exception as exc:  # pragma: no cover - only hit when deps are absent.
        raise RuntimeError(
            "LangChain 1.x dependencies are not installed. Run pip install -r requirements.txt."
        ) from exc

    args_schema = args_schema_from_openai_schema(tool)

    async def _coroutine(**kwargs: Any) -> str:
        tool_call_id = f"lc_tool_{uuid.uuid4().hex}"
        await emit(
            ToolCallEvent(
                tool_name=tool.name,
                tool_args=kwargs,
                step_id=1,
                tool_call_id=tool_call_id,
                session_id=session_id,
            )
        )

        try:
            result = await tool.execute(**kwargs)
        except Exception as exc:
            logger.exception("[LangChainV1] tool %s failed", tool.name)
            await emit(
                ToolResultEvent(
                    tool_name=tool.name,
                    result=str(exc),
                    step_id=1,
                    tool_call_id=tool_call_id,
                    is_error=True,
                    session_id=session_id,
                )
            )
            raise

        output = tool_result_to_text(result)
        await emit(
            ToolResultEvent(
                tool_name=tool.name,
                result=output,
                step_id=1,
                tool_call_id=tool_call_id,
                is_error=bool(getattr(result, "error", None)),
                structured_data=extract_structured_data(result),
                session_id=session_id,
            )
        )
        return output

    _coroutine.__name__ = tool.name
    _coroutine.__doc__ = tool.description or f"Execute {tool.name}."

    return StructuredTool.from_function(
        name=tool.name,
        description=tool.description or tool.name,
        coroutine=_coroutine,
        args_schema=args_schema,
    )
