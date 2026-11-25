"""Módulo do agente autônomo de atendimento ao cliente (TP4)."""

from .support_agent import (
    CUSTOMER_SUPPORT_SYSTEM_PROMPT,
    SupportDeskClient,
    SupportDeskConfig,
    build_groq_model,
    build_support_agent,
    make_classify_tool,
)

__all__ = [
    "CUSTOMER_SUPPORT_SYSTEM_PROMPT",
    "SupportDeskClient",
    "SupportDeskConfig",
    "build_groq_model",
    "build_support_agent",
    "make_classify_tool",
]
