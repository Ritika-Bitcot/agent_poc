"""Agent factory using LangChain's latest create_agent API with structured output."""

import json
from typing import Any, Optional

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.memory import get_conversation_memory
from app.models.response_models import (
    AccountOverview,
    AgentResponse,
    FacilityOverview,
    NoteOverview,
)
from app.prompts import get_agent_prompt
from app.tools import (
    fetch_account_details,
    fetch_facility_details,
    fetch_notes,
    save_notes,
)

# Global agent instance
_agent = None


def _determine_card_key(
    query: str,
    tools_called: set,
    account_data: list,
    facility_data: list,
    notes_data: list,
) -> str:
    """
    Intelligently determine the card_key based on which tools were called
    and what data was fetched.

    Args:
        query: The user's original query
        tools_called: Set of tool names that were called
        account_data: Account data that was fetched
        facility_data: Facility data that was fetched
        notes_data: Notes data that was fetched

    Returns:
        The appropriate card_key
    """
    # Check which tools were called
    if "fetch_notes" in tools_called or "save_notes" in tools_called:
        return "notes_overview"

    # Check if both account and facility data were fetched (account overview scenario)
    if account_data and facility_data:
        return "account_overview"

    # Check if only facility data was fetched
    if facility_data and not account_data:
        return "facility_overview"

    # Check if account data was fetched
    if account_data:
        # Check if query is about account overview specifically
        query_lower = query.lower()
        if any(
            keyword in query_lower
            for keyword in ["account overview", "show account", "account details"]
        ):
            return "account_overview"
        # Otherwise it's a specific account question
        return "other"

    # Default to other
    return "other"


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
    prompt = get_agent_prompt()

    # Create agent using the latest create_agent API
    agent = create_agent(
        model=llm, tools=tools, system_prompt=prompt.format_messages()[0].content
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


def _prepare_message_with_context(
    text: str, account_id: str, user_id: str, facility_id: Optional[str] = None
) -> str:
    """
    Prepare message content with context for the agent.

    Args:
        text: User's query
        account_id: Account ID
        user_id: User ID
        facility_id: Optional facility ID

    Returns:
        Formatted message content
    """
    facility_context = (
        f"- Facility ID: {facility_id} "
        f"(use this facility_id when calling fetch_facility_details tool)"
        if facility_id
        else ""
    )

    return f"""User Query: {text}

Context:
- Account ID: {account_id} (use this account_id when calling
  fetch_account_details tool)
- User ID: {user_id} (use this user_id when calling fetch_notes tool)
{facility_context}

Please help the user with their request. Use the available tools with the IDs
provided above to fetch the necessary data."""


def _extract_tool_data(messages: list) -> tuple[list, list, list, set]:
    """
    Extract account, facility, and notes data from tool messages.

    Args:
        messages: List of messages from agent result

    Returns:
        Tuple of (account_data, facility_data, notes_data, tools_called)
    """
    account_data = []
    facility_data = []
    notes_data = []
    tools_called = set()

    for msg in messages:
        if isinstance(msg, ToolMessage):
            tools_called.add(msg.name if hasattr(msg, "name") else "unknown")

            if hasattr(msg, "content") and msg.content:
                content = msg.content
                tool_result = None

                if isinstance(content, dict):
                    tool_result = content
                elif isinstance(content, str):
                    try:
                        tool_result = json.loads(content)
                    except json.JSONDecodeError:
                        tool_result = None

                if isinstance(tool_result, dict):
                    if "account_overview" in tool_result:
                        account_data = tool_result.get("account_overview", [])
                    if "facility_overview" in tool_result:
                        facility_data = tool_result.get("facility_overview", [])
                    if "note_overview" in tool_result:
                        notes_data = tool_result.get("note_overview", [])
        elif hasattr(msg, "tool_calls") and msg.tool_calls:
            for tool_call in msg.tool_calls:
                if hasattr(tool_call, "name"):
                    tools_called.add(tool_call.name)
        elif hasattr(msg, "name") and msg.name:
            tools_called.add(msg.name)

    return account_data, facility_data, notes_data, tools_called


def _extract_agent_response(messages: list) -> tuple[str, bool]:
    """
    Extract the agent's actual response from messages.

    Args:
        messages: List of messages from agent result

    Returns:
        Tuple of (response_content, agent_responded)
    """
    response_content = ""
    agent_responded = False

    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            continue

        if isinstance(msg, AIMessage) and hasattr(msg, "content") and msg.content:
            content_stripped = msg.content.strip()

            # Skip if content is too short or contains context/prompt markers
            skip_phrases = [
                "User Query:",
                "Context:",
                "Please help",
                "I'll help",
            ]

            if len(content_stripped) > 10 and not any(
                skip in content_stripped for skip in skip_phrases
            ):
                response_content = content_stripped
                agent_responded = True
                break

    return response_content, agent_responded


def _generate_fallback_response(
    account_data: list, facility_data: list, notes_data: list
) -> str:
    """
    Generate fallback response when agent doesn't respond properly.

    Args:
        account_data: Account data fetched
        facility_data: Facility data fetched
        notes_data: Notes data fetched

    Returns:
        Fallback response message
    """
    if account_data or facility_data or notes_data:
        return (
            "I apologize, but I couldn't generate a proper response. "
            "Please try rephrasing your question or ask about your account, "
            "facilities, or notes."
        )
    return (
        "I apologize, but I couldn't process your request. "
        "Please try asking about your account, facilities, or notes."
    )


def _convert_to_pydantic_models(
    account_data: list, facility_data: list, notes_data: list
) -> tuple[list, Optional[list], list]:
    """
    Convert raw data dictionaries to Pydantic models.

    Args:
        account_data: List of account dictionaries
        facility_data: List of facility dictionaries
        notes_data: List of note dictionaries

    Returns:
        Tuple of (account_models, facility_models, note_models)
    """
    account_models = []
    for account in account_data:
        try:
            account_models.append(AccountOverview(**account))
        except ValidationError:
            continue

    facility_models = None
    if facility_data:
        facility_models = []
        for facility in facility_data:
            try:
                facility_models.append(FacilityOverview(**facility))
            except ValidationError:
                continue
        facility_models = facility_models if facility_models else None

    note_models = []
    for note in notes_data:
        try:
            note_models.append(NoteOverview(**note))
        except ValidationError:
            continue

    return account_models, facility_models, note_models


def _build_agent_response(
    conversation_id: str,
    response_content: str,
    card_key: str,
    account_models: list,
    facility_models: Optional[list],
    note_models: list,
) -> AgentResponse:
    """
    Build the final AgentResponse using Pydantic model.

    Args:
        conversation_id: Conversation identifier
        response_content: Agent's response text
        card_key: UI card type
        account_models: List of AccountOverview models
        facility_models: Optional list of FacilityOverview models
        note_models: List of NoteOverview models

    Returns:
        Validated AgentResponse instance
    """
    return AgentResponse(
        conversation_id=conversation_id,
        final_response=response_content,
        card_key=card_key,
        account_overview=account_models,
        facility_overview=facility_models,
        note_overview=note_models,
        rewards_overview=None,
        order_overview=None,
    )


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

    This is the main orchestrator function that coordinates the agent
    processing workflow. It delegates specific responsibilities to focused
    helper functions.

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
    # Invoke agent with conversation memory
    # Wrap all operations in try-except to ensure consistent error handling
    try:
        # Manage conversation context
        conv_memory = get_conversation_memory()
        final_conversation_id = conv_memory.get_or_create_conversation_id(
            user_id, conversation_id
        )

        # Prepare message with context
        message_content = _prepare_message_with_context(
            text, account_id, user_id, facility_id
        )
        human_message = HumanMessage(content=message_content)
        agent_input = {"messages": [human_message]}

        # Save human message to conversation memory
        conv_memory.add_message(final_conversation_id, human_message)

        # Invoke agent with conversation memory
        result = agent.invoke(
            agent_input, config={"configurable": {"thread_id": final_conversation_id}}
        )

        # Process agent result
        if isinstance(result, dict) and "messages" in result:
            messages = result["messages"]

            # Extract tool data
            account_data, facility_data, notes_data, tools_called = _extract_tool_data(
                messages
            )

            # Extract agent response
            response_content, agent_responded = _extract_agent_response(messages)

            # Handle fallback if agent didn't respond
            if not agent_responded:
                response_content = _generate_fallback_response(
                    account_data, facility_data, notes_data
                )

        else:
            response_content = str(result)
            account_data = []
            facility_data = []
            notes_data = []
            tools_called = set()

        # Determine card key for UI
        card_key = _determine_card_key(
            text, tools_called, account_data, facility_data, notes_data
        )

        # Convert to Pydantic models
        account_models, facility_models, note_models = _convert_to_pydantic_models(
            account_data, facility_data, notes_data
        )

        # Save AI response to conversation memory
        ai_message = AIMessage(content=response_content)
        conv_memory.add_message(final_conversation_id, ai_message)

        # Build and return response
        return _build_agent_response(
            final_conversation_id,
            response_content,
            card_key,
            account_models,
            facility_models,
            note_models,
        )

    except Exception as e:
        # Error handling - return consistent error response
        # Handle case where conversation_id might not be set if error occurred early
        error_response = (
            f"I apologize, but I encountered an error processing your request: {str(e)}"
        )

        # Try to save error to conversation memory if available
        try:
            conv_memory = get_conversation_memory()
            # Try to get conversation_id - may fail if setup didn't complete
            try:
                final_conversation_id = conv_memory.get_or_create_conversation_id(
                    user_id, conversation_id
                )
                ai_message = AIMessage(content=error_response)
                conv_memory.add_message(final_conversation_id, ai_message)
                error_conversation_id = final_conversation_id
            except Exception:
                # If conversation setup fails, use provided conversation_id
                # or generate fallback
                error_conversation_id = conversation_id or "error"
        except Exception:
            # If memory system is unavailable, use fallback
            error_conversation_id = conversation_id or "error"

        return _build_agent_response(
            error_conversation_id,
            error_response,
            "other",
            [],
            None,
            [],
        )
