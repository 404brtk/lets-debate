import asyncio
import logging
from dataclasses import dataclass, field
from typing import AsyncIterator

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

# ── Role-specific system prompt templates ──────────────────────────────

ROLE_PROMPTS: dict[str, str] = {
    "skeptic": (
        "You are {name}, a critical skeptic and devil's advocate. "
        "Challenge assumptions, poke holes in arguments, demand evidence, "
        "and highlight risks or overlooked downsides. Be sharp but fair."
    ),
    "optimist": (
        "You are {name}, an enthusiastic optimist. "
        "Highlight opportunities, positive outcomes, and creative possibilities. "
        "Acknowledge valid concerns but reframe them constructively."
    ),
    "expert": (
        "You are {name}, a domain expert. "
        "Provide factual, well-researched analysis grounded in evidence. "
        "Cite specific data points, research, or established principles."
    ),
    "pragmatist": (
        "You are {name}, a practical pragmatist. "
        "Focus on real-world feasibility, implementation details, costs, "
        "and actionable steps. Bridge theory and practice."
    ),
    "synthesizer": (
        "You are {name}, a balanced synthesizer. "
        "Identify common ground between different viewpoints, summarize key "
        "arguments, and propose integrative solutions."
    ),
}

DEBATE_CONTEXT_TEMPLATE = (
    "\n\nYou are participating in a structured debate on the topic:\n"
    '"{topic}"\n'
    "{description_block}"
    "\nRespond concisely in 2-4 sentences. Be direct and pithy. "
    "Address the previous speakers' points directly when relevant. Stay in character."
)

CONSENSUS_PROMPT = (
    "You are a neutral judge drawing a final conclusion for a multi-agent debate.\n\n"
    "Topic: \"{topic}\"\n\n"
    "Full debate transcript:\n{transcript}\n\n"
    "Write a clear, definitive conclusion in 3-5 sentences. "
    "State plainly what the participants agreed on, where they disagreed, "
    "and what the most compelling takeaway is. "
    "Write as a decisive verdict — not a wishy-washy summary. "
    "Do NOT use bullet points, headers, or labels. Just write plain prose."
)


@dataclass
class AgentSpec:
    """Agent specification for the debate graph."""

    id: str
    name: str
    role: str
    model_provider: str  # "openai" | "gemini"
    model_name: str
    temperature: float
    system_prompt: str
    order_index: int


@dataclass
class DebateGraphState:
    """Mutable state flowing through the LangGraph debate graph."""

    topic: str
    description: str
    agents: list[AgentSpec]
    api_keys: dict[str, str | None]  # {"openai": "sk-...", "google": "AIza..."}
    messages: list[dict] = field(default_factory=list)
    current_agent_index: int = 0
    turn_count: int = 0
    max_turns: int = 20


def create_chat_model(
    provider: str,
    model_name: str,
    api_key: str | None,
    temperature: float = 0.7,
):
    """Create a LangChain chat model for the given provider."""
    if provider == "openai":
        return init_chat_model(
            model=model_name,
            model_provider="openai",
            api_key=api_key,
            temperature=temperature,
        )
    elif provider == "gemini":
        return init_chat_model(
            model=model_name,
            model_provider="google_genai",
            api_key=api_key,
            temperature=temperature,
        )
    elif provider == "ollama":
        from app.config import get_settings

        settings = get_settings()
        return init_chat_model(
            model=model_name,
            model_provider="ollama",
            base_url=settings.OLLAMA_BASE_URL,
            temperature=temperature,
        )
    else:
        raise ValueError(f"Unsupported model provider: {provider}")


def build_system_prompt(agent: AgentSpec, topic: str, description: str = "") -> str:
    """Build the full system prompt for an agent."""
    role_prompt = ROLE_PROMPTS.get(agent.role, ROLE_PROMPTS["expert"]).format(
        name=agent.name
    )
    description_block = f'\nContext: "{description}"\n' if description else ""
    context = DEBATE_CONTEXT_TEMPLATE.format(
        topic=topic, description_block=description_block
    )
    return role_prompt + context


def _get_api_key_for_provider(provider: str, api_keys: dict[str, str | None]) -> str | None:
    """Resolve the API key for a given provider."""
    if provider == "ollama":
        return None
    key_map = {"openai": "openai", "gemini": "google"}
    key_name = key_map.get(provider)
    if not key_name:
        raise ValueError(f"Unknown provider: {provider}")
    key = api_keys.get(key_name)
    if not key:
        raise ValueError(
            f"No API key configured for provider '{provider}'. "
            "Please add your API key in your profile settings."
        )
    return key


async def run_debate_turn(
    state: DebateGraphState,
) -> AsyncIterator[dict]:
    """Run a single debate turn: one agent speaks.

    Yields event dicts:
        {"type": "agent_thinking", "agent": AgentSpec}
        {"type": "agent_token", "agent": AgentSpec, "token": str}
        {"type": "agent_spoke", "agent": AgentSpec, "content": str, "turn": int}
    """
    if state.current_agent_index >= len(state.agents):
        state.current_agent_index = 0

    agent = state.agents[state.current_agent_index]

    yield {"type": "agent_thinking", "agent": agent}

    api_key = _get_api_key_for_provider(agent.model_provider, state.api_keys)
    llm = create_chat_model(
        provider=agent.model_provider,
        model_name=agent.model_name,
        api_key=api_key,
        temperature=agent.temperature,
    )

    system_prompt = build_system_prompt(agent, state.topic, state.description)

    # Build message history for the LLM
    lc_messages = [SystemMessage(content=system_prompt)]

    for msg in state.messages:
        if msg.get("agent_name") == agent.name:
            lc_messages.append(AIMessage(content=msg["content"]))
        else:
            prefix = f"[{msg['agent_name']}]: "
            lc_messages.append(HumanMessage(content=prefix + msg["content"]))

    if not state.messages:
        lc_messages.append(
            HumanMessage(
                content=f"The debate begins. Please present your opening argument on: {state.topic}"
            )
        )
    else:
        lc_messages.append(
            HumanMessage(
                content="Please respond to the discussion above, staying in your role."
            )
        )

    # Stream the response token by token
    full_content = ""
    async for chunk in llm.astream(lc_messages):
        token = chunk.content
        if token:
            full_content += token
            yield {"type": "agent_token", "agent": agent, "token": token}

    state.turn_count += 1
    state.messages.append(
        {
            "agent_id": agent.id,
            "agent_name": agent.name,
            "content": full_content,
            "turn_number": state.turn_count,
            "role": agent.role,
        }
    )
    state.current_agent_index = (state.current_agent_index + 1) % len(state.agents)

    yield {
        "type": "agent_spoke",
        "agent": agent,
        "content": full_content,
        "turn": state.turn_count,
    }


async def run_full_debate(
    state: DebateGraphState,
    stop_event: asyncio.Event | None = None,
    human_message_queue: asyncio.Queue | None = None,
) -> AsyncIterator[dict]:
    """Run the full debate until max_turns or stopped.

    Yields all events from run_debate_turn for each turn.
    Between turns, checks for stop signal and drains human messages.
    """
    while state.turn_count < state.max_turns:
        # Check stop signal before each turn
        if stop_event is not None and stop_event.is_set():
            yield {"type": "debate_paused", "total_turns": state.turn_count}
            return

        # Drain human messages injected between turns
        if human_message_queue is not None:
            while not human_message_queue.empty():
                try:
                    human_msg = human_message_queue.get_nowait()
                    state.messages.append(human_msg)
                    yield {"type": "human_injected", "message": human_msg}
                except asyncio.QueueEmpty:
                    break

        async for event in run_debate_turn(state):
            yield event

    yield {"type": "debate_completed", "total_turns": state.turn_count}


async def generate_consensus(
    state: DebateGraphState,
) -> AsyncIterator[dict]:
    """Generate a conclusion after a completed debate.

    Yields:
        {"type": "consensus_token", "token": str}
        {"type": "consensus_complete", "summary": str}
    """
    transcript_lines = []
    for msg in state.messages:
        transcript_lines.append(f"[{msg['agent_name']}] (Turn {msg['turn_number']}): {msg['content']}")
    transcript = "\n\n".join(transcript_lines)

    prompt = CONSENSUS_PROMPT.format(topic=state.topic, transcript=transcript)

    first_agent = state.agents[0]
    api_key = _get_api_key_for_provider(first_agent.model_provider, state.api_keys)
    llm = create_chat_model(
        provider=first_agent.model_provider,
        model_name=first_agent.model_name,
        api_key=api_key,
        temperature=0.3,
    )

    full_content = ""
    async for chunk in llm.astream([HumanMessage(content=prompt)]):
        token = chunk.content
        if token:
            full_content += token
            yield {"type": "consensus_token", "token": token}

    yield {
        "type": "consensus_complete",
        "summary": full_content.strip(),
    }
