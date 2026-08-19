from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from backend.agent.schema import Message, Role
from backend.agent.tool.resume_data_store import ResumeDataStore
from backend.agent.web.streaming.events import (
    AgentEndEvent,
    AgentErrorEvent,
    AgentStartEvent,
    AnswerEvent,
    ResumeUpdatedEvent,
    StreamEvent,
    ThoughtEvent,
)
from backend.core.logger import get_logger

from backend.agent.langchain_v1.tools import adapt_tool_for_langchain

logger = get_logger(__name__)


LANGCHAIN_V1_SYSTEM_PROMPT = """你是「一语简历」的 LangChain 1.x Agent Runtime。
你需要围绕当前简历 JSON 完成生成、读取、诊断、局部修改和优化任务。

执行规则：
1. 每轮先理解用户意图，再选择一个最合适的工具；不要绕过工具直接编造简历数据。
2. 修改简历时必须调用 cv_editor_agent，并使用精确 JSON path、action 和 value。
3. 诊断简历时调用 cv_analyzer_agent；展示或加载简历时调用 show_resume/list_resumes/get_resume_detail/cv_reader_agent。
4. 从零生成简历时调用 generate_resume。
5. 工具执行完成后，用中文简短总结本轮完成了什么，以及用户下一步可以做什么。
"""


class LangChainV1ResumeRunner:
    """Run the existing resume tools through LangChain 1.x create_agent."""

    def __init__(
        self,
        *,
        session_id: str,
        agent: Any,
        chat_history_manager: Any | None = None,
    ) -> None:
        self.session_id = session_id
        self.agent = agent
        self.chat_history_manager = chat_history_manager

    def _build_model(self) -> Any:
        try:
            from langchain_openai import ChatOpenAI
        except Exception as exc:  # pragma: no cover - only hit when deps are absent.
            raise RuntimeError(
                "LangChain 1.x OpenAI integration is not installed. "
                "Run pip install -r requirements.txt."
            ) from exc

        llm = getattr(self.agent, "llm", None)
        if llm is None:
            raise RuntimeError("Current Manus agent has no initialized LLM.")

        kwargs: dict[str, Any] = {
            "model": llm.model,
            "api_key": llm.api_key,
            "base_url": llm.base_url,
            "temperature": getattr(llm, "temperature", 0.2),
            "timeout": 300,
            "max_retries": 3,
        }
        extra_body = getattr(llm, "extra_body", None)
        if extra_body:
            kwargs["extra_body"] = extra_body
        return ChatOpenAI(**kwargs)

    def _history_to_langchain_messages(self) -> list[dict[str, Any]]:
        raw_messages: list[Any] = []
        if self.chat_history_manager is not None:
            raw_messages = self.chat_history_manager.get_messages(max_messages=20)
        elif getattr(self.agent, "memory", None) is not None:
            raw_messages = self.agent.memory.messages[-20:]

        messages: list[dict[str, Any]] = []
        for msg in raw_messages:
            role = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
            content = msg.content or ""
            if not content or role == "tool":
                continue
            if role not in {"system", "user", "assistant"}:
                continue
            messages.append({"role": role, "content": content})
        return messages

    @staticmethod
    def _extract_final_answer(result: Any) -> str:
        if isinstance(result, dict):
            messages = result.get("messages") or []
            for msg in reversed(messages):
                content = getattr(msg, "content", None)
                if content is None and isinstance(msg, dict):
                    content = msg.get("content")
                if isinstance(content, list):
                    parts = []
                    for item in content:
                        if isinstance(item, dict):
                            parts.append(str(item.get("text") or item.get("content") or ""))
                        else:
                            parts.append(str(item))
                    content = "".join(parts)
                if content:
                    return str(content)
        return str(result or "")

    async def stream(self) -> AsyncIterator[StreamEvent]:
        event_queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()

        async def emit(event: StreamEvent) -> None:
            await event_queue.put(event)

        yield AgentStartEvent(
            agent_name="LangChainV1ResumeAgent",
            task="resume_agent_runtime",
            session_id=self.session_id,
        )
        yield ThoughtEvent(
            thought="已启用 LangChain 1.x create_agent 运行时，正在把现有简历工具注册为标准 Tool。",
            step_id=1,
            session_id=self.session_id,
            node_id="langchain_v1:init",
            phase="runtime_init",
        )

        async def _producer() -> None:
            try:
                try:
                    from langchain.agents import create_agent
                except Exception as exc:  # pragma: no cover - only hit when deps are absent.
                    raise RuntimeError(
                        "LangChain 1.x is not installed. Run pip install -r requirements.txt."
                    ) from exc

                tools = [
                    adapt_tool_for_langchain(tool, session_id=self.session_id, emit=emit)
                    for tool in getattr(self.agent.available_tools, "tools", [])
                    if tool.name not in {"terminate", "ask_human"}
                ]
                lc_agent = create_agent(
                    model=self._build_model(),
                    tools=tools,
                    system_prompt=LANGCHAIN_V1_SYSTEM_PROMPT,
                )
                result = await lc_agent.ainvoke(
                    {"messages": self._history_to_langchain_messages()}
                )

                final_answer = self._extract_final_answer(result).strip()
                if not final_answer:
                    final_answer = "本轮 LangChain 1.x Agent 已完成执行。"

                resume_data = ResumeDataStore.get_data(self.session_id)
                if isinstance(resume_data, dict):
                    await emit(ResumeUpdatedEvent(resume_data, session_id=self.session_id))

                await emit(AnswerEvent(final_answer, session_id=self.session_id))
                if self.chat_history_manager is not None:
                    self.chat_history_manager.add_message(
                        Message(role=Role.ASSISTANT, content=final_answer),
                        persist=True,
                    )
                await emit(
                    AgentEndEvent(
                        agent_name="LangChainV1ResumeAgent",
                        success=True,
                        session_id=self.session_id,
                    )
                )
            except Exception as exc:
                logger.exception("[LangChainV1] runtime failed")
                await emit(
                    AgentErrorEvent(
                        error_message=str(exc),
                        error_type=type(exc).__name__,
                        session_id=self.session_id,
                    )
                )
                await emit(
                    AgentEndEvent(
                        agent_name="LangChainV1ResumeAgent",
                        success=False,
                        session_id=self.session_id,
                    )
                )
            finally:
                await event_queue.put(None)

        task = asyncio.create_task(_producer())
        try:
            while True:
                event = await event_queue.get()
                if event is None:
                    break
                yield event
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
