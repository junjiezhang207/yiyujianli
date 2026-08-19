"""LangChain 1.x runtime integration for the resume agent.

The project keeps its original Manus runtime as the default path.  This package
adapts the existing resume tools to LangChain 1.x so the new runtime can be
enabled per request or by environment variable without rewriting the business
logic.
"""

from backend.agent.langchain_v1.runner import LangChainV1ResumeRunner

__all__ = ["LangChainV1ResumeRunner"]
