"""Agent factory using LangChain's latest create_agent API with structured output."""

import json
from typing import Any, Optional

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.memory import get_conversation_memory
from app.models.response_models import AgentResponse
from app.prompts.agent_prompts import get_response_schema
from app.tools import (
    fetch_account_details,
    fetch_facility_details,
    fetch_notes,
    save_notes,
)

# Global agent instance
_agent = None


def create_agent_instance(openai_api_key: str, model_name: str = "gpt-4o-mini") -> Any:
    """
    Create the agent using LangChain's create_agent API with structured output.

    Args:
        openai_api_key: OpenAI API key
        model_name: Model name to use (default: gpt-4o-mini)

    Returns:
        Configured agent
    """
    # Initialize the language model
    llm = ChatOpenAI(
        api_key=openai_api_key, model=model_name, temperature=0.1, max_tokens=2000
    )

    # Get the tools
    tools = [fetch_account_details, fetch_facility_details, save_notes, fetch_notes]

    # Get the prompt template
    from app.prompts import get_agent_prompt

    prompt = get_agent_prompt()

    # Create agent using the latest create_agent API
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=prompt.format_messages()[0].content,
        response_format=get_response_schema(),
    )

    return agent


def get_agent(openai_api_key: str) -> Any:
    """
    Get the global agent instance, creating it if necessary.

    Args:
        openai_api_key: OpenAI API key

    Returns:
        Agent instance
    """
    global _agent
    if _agent is None:
        _agent = create_agent_instance(openai_api_key)
    return _agent


def process_agent_request(
    agent: Any,
    text: str,
    user_id: str,
    account_id: str,
    facility_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> AgentResponse:
    """
    Process a request through the agent and return structured response.

    Args:
        agent: The agent instance
        text: User's message
        user_id: User ID
        account_id: Account ID
        facility_id: Optional facility ID
        conversation_id: Optional conversation ID

    Returns:
        Structured agent response
    """
    # Get or create conversation ID
    conv_memory = get_conversation_memory()
    final_conversation_id = conv_memory.get_or_create_conversation_id(
        user_id, conversation_id
    )

    # Create message with minimal context; the agent should infer and call tools.
    message_content = (
        "User Query: "
        + text
        + "\n\nContext:\n"
        + f"- Account ID: {account_id}\n"
        + f"- User ID: {user_id}\n"
        + (f"- Facility ID: {facility_id}\n" if facility_id else "")
        + "\nRespond with a single JSON object matching the required schema."
    )

    # Prepare input for the agent
    human_message = HumanMessage(content=message_content)
    agent_input = {"messages": [human_message]}

    # Save the human message to conversation memory
    conv_memory.add_message(final_conversation_id, human_message)

    # Run the agent with conversation memory
    try:
        result = agent.invoke(
            agent_input,
            config={
                "configurable": {
                    "thread_id": final_conversation_id,
                    "user_id": user_id,
                    "account_id": account_id,
                    "facility_id": facility_id or "",
                }
            },
        )

        # Attempt to parse a structured JSON response from the final AI message
        response_payload: Optional[dict] = None
        if isinstance(result, dict) and "messages" in result:
            messages = result["messages"]
            # Traverse from the end to find the final AI JSON block
            for msg in reversed(messages):
                content = getattr(msg, "content", None)
                if isinstance(content, str) and content.strip():
                    try:
                        candidate = json.loads(content)
                        if isinstance(candidate, dict) and {
                            "final_response",
                            "card_key",
                        }.issubset(candidate.keys()):
                            response_payload = candidate
                            break
                    except json.JSONDecodeError:
                        continue

        # Fallback: if the invoke returned a dict that itself is the payload
        if response_payload is None and isinstance(result, dict):
            keys = set(result.keys())
            if {"final_response", "card_key"}.issubset(keys):
                response_payload = result

        # Absolute fallback to plain text
        if response_payload is None:
            plain_text = str(result)
            ai_message = AIMessage(content=plain_text)
            conv_memory.add_message(final_conversation_id, ai_message)
            return AgentResponse(
                conversation_id=final_conversation_id,
                final_response=plain_text,
                card_key="other",
                account_overview=[],
                facility_overview=None,
                note_overview=[],
                rewards_overview=None,
                order_overview=None,
            )

        # Ensure conversation_id is set
        response_payload.setdefault("conversation_id", final_conversation_id)

        # Persist the final_response to conversation memory
        ai_message = AIMessage(content=response_payload.get("final_response", ""))
        conv_memory.add_message(final_conversation_id, ai_message)

        # Normalize optional arrays
        account_overview = response_payload.get("account_overview") or []
        facility_overview = response_payload.get("facility_overview") or None
        note_overview = response_payload.get("note_overview") or []

        return AgentResponse(
            conversation_id=response_payload.get(
                "conversation_id", final_conversation_id
            ),
            final_response=response_payload.get("final_response", ""),
            card_key=response_payload.get("card_key", "other"),
            account_overview=account_overview,
            facility_overview=facility_overview,
            note_overview=note_overview,
            rewards_overview=response_payload.get("rewards_overview"),
            order_overview=response_payload.get("order_overview"),
        )

    except Exception as e:
        # Error fallback
        error_response = (
            f"I apologize, but I encountered an error processing your request: {str(e)}"
        )

        # Save the error response to conversation memory
        ai_message = AIMessage(content=error_response)
        conv_memory.add_message(final_conversation_id, ai_message)

        return AgentResponse(
            conversation_id=final_conversation_id,
            final_response=error_response,
            card_key="other",
            account_overview=[],
            facility_overview=None,
            note_overview=[],
            rewards_overview=None,
            order_overview=None,
        )
