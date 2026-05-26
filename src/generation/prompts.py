from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

_RAG_SYSTEM_V1 = (
    "You are a helpful assistant. Answer the question using only the context provided.\n"
    "If the context lacks sufficient information, say: "
    "'I don't have enough information to answer this question.'\n"
    "Do not fabricate facts. Be concise and accurate.\n\n"
    "Context:\n{context}"
)

_RAG_SYSTEM_V2 = (
    "You are a helpful assistant. Answer the question using only the context provided.\n"
    "Reason step by step before giving your final answer.\n"
    "If the context lacks sufficient information, say: "
    "'I don't have enough information to answer this question.'\n\n"
    "Context:\n{context}"
)

PROMPT_REGISTRY: dict[str, ChatPromptTemplate] = {
    "v1": ChatPromptTemplate.from_messages([("system", _RAG_SYSTEM_V1), ("human", "{question}")]),
    "v2": ChatPromptTemplate.from_messages(
        [("system", _RAG_SYSTEM_V2), ("human", "{question}\n\nStep-by-step answer:")]
    ),
}


def get_prompt(version: str = "v1") -> ChatPromptTemplate:
    if version not in PROMPT_REGISTRY:
        available = list(PROMPT_REGISTRY)
        raise ValueError(f"Unknown prompt version '{version}'. Available: {available}")
    return PROMPT_REGISTRY[version]
