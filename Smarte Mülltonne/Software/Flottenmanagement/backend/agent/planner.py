from langchain_groq import ChatGroq
from langchain.agents import create_agent

from agent.prompts import SYSTEM_PROMPT
from agent.tools import ALL_TOOLS
from config import settings


def build_agent():
    """Tool-calling agent via Groq (Llama 3.3 70B) as LangGraph CompiledStateGraph."""
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=settings.groq_api_key,
        temperature=0,
    )
    return create_agent(
        model=llm,
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )


# Singleton — avoids rebuilding on every request
_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent
