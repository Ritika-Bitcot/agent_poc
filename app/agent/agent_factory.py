"""Agent factory using LangChain's latest create_agent API with structured output."""

import json
from typing import Any, Optional

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.memory import get_conversation_memory
from app.models.response_models import AgentResponse
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


def _generate_response_from_data(
    query: str, account_data: list, facility_data: list, notes_data: list
) -> str:
    """
    Generate a natural language response based on the fetched data.

    Args:
        query: The user's original query
        account_data: Account data that was fetched
        facility_data: Facility data that was fetched
        notes_data: Notes data that was fetched

    Returns:
        Natural language response
    """
    query_lower = query.lower()

    # Account overview response
    if account_data and any(
        keyword in query_lower
        for keyword in ["account", "overview", "summary", "show account"]
    ):
        account = account_data[0]

        # Format address
        address_parts = [
            account.get("address_line1", ""),
            account.get("address_city", ""),
            account.get("address_state", ""),
        ]
        address = ", ".join(filter(None, address_parts))
        if account.get("address_postal_code"):
            address += f" {account.get('address_postal_code')}"

        # Prepare values for long lines
        current_tier = account.get("current_tier", "N/A")
        next_tier_val = account.get("next_tier", "N/A")
        points_needed_val = account.get("points_to_next_tier", 0)
        current_balance = account.get("current_balance", 0)
        pending_balance = account.get("pending_balance", 0)
        rewards_redeemed = account.get("rewards_redeemed_towards_next_free_vial", 0)
        rewards_required = account.get("rewards_required_for_next_free_vial", 0)

        response = f"""Here is a summary of your account:

- Account Name: {account.get('name', 'N/A')}
- Status: {account.get('status', 'N/A')}
- Account ID: {account.get('account_id', 'N/A')}
- Address: {address}
- Pricing Model: {account.get('pricing_model', 'N/A')}

Loyalty & Rewards:
- Current Loyalty Tier: {current_tier} (next tier: {next_tier_val}, {points_needed_val} points needed)  # noqa: E501
- Loyalty Points Balance: {current_balance} (pending: {pending_balance})
- Free Vials Available: {account.get('free_vials_available', 0)}
- Rewards Redeemed Toward Next Free Vial: {rewards_redeemed} ({rewards_required} needed for next free vial)  # noqa: E501

Other Details:
- Evolux Level: {account.get('evolux_level', 'N/A')}
- Reward Program Opt-in Status: {account.get('rewards_status', 'N/A')}

Let me know if you need more detailed information or have other questions!"""

        # Add facility information if available
        if facility_data:
            response += f"\n\nFacilities ({len(facility_data)} total):\n"
            for i, facility in enumerate(facility_data, 1):
                name = facility.get("name", "N/A")
                fac_id = facility.get("id", "N/A")
                status = facility.get("status", "N/A")
                response += f"{i}. {name} ({fac_id}) - Status: {status}\n"

        return response

    # Facility overview response
    elif facility_data and any(
        keyword in query_lower for keyword in ["facility", "facilities"]
    ):
        if len(facility_data) == 1:
            facility = facility_data[0]
            # Prepare values for long lines
            account_name = facility.get("account_name", "N/A")
            account_id_val = facility.get("account_id", "N/A")
            shipping_line1 = facility.get("shipping_address_line1", "N/A")
            shipping_city = facility.get("shipping_address_city", "N/A")
            shipping_state = facility.get("shipping_address_state", "N/A")
            shipping_zip = facility.get("shipping_address_zip", "N/A")
            license_num = facility.get("medical_license_number", "N/A")
            license_status = facility.get("medical_license_status", "N/A")
            owner_first = facility.get("medical_license_owner_first_name", "N/A")
            owner_last = facility.get("medical_license_owner_last_name", "N/A")
            agreement_status = facility.get("agreement_status", "N/A")
            agreement_type = facility.get("agreement_type", "N/A")

            return f"""Here is a summary of your facility:

- Facility Name: {facility.get('name', 'N/A')}
- Status: {facility.get('status', 'N/A')}
- Facility ID: {facility.get('id', 'N/A')}
- Account: {account_name} ({account_id_val})
- Shipping Address: {shipping_line1}, {shipping_city}, {shipping_state} {shipping_zip}
- Medical License: {license_num} ({license_status})
- License Owner: {owner_first} {owner_last}
- Agreement Status: {agreement_status} ({agreement_type})

Let me know if you need more detailed information or have other questions!"""
        else:
            response = f"Here are all your facilities ({len(facility_data)} total):\n\n"
            for i, facility in enumerate(facility_data, 1):
                name = facility.get("name", "N/A")
                fac_id = facility.get("id", "N/A")
                status = facility.get("status", "N/A")
                response += f"{i}. {name} ({fac_id}) - Status: {status}\n"
            response += (
                "\nLet me know if you need more detailed information "
                "about any specific facility!"
            )
            return response

    # Notes overview response
    elif notes_data and any(
        keyword in query_lower for keyword in ["notes", "note", "meeting"]
    ):
        if not notes_data:
            return "You don't have any notes saved yet."
        else:
            response = f"Here are your notes ({len(notes_data)} total):\n\n"
            for i, note in enumerate(notes_data, 1):
                created_at = note.get("created_at", "")
                date_str = created_at.split("T")[0] if "T" in created_at else created_at
                time_str = (
                    created_at.split("T")[1].split(".")[0] if "T" in created_at else ""
                )

                response += f"{i}. {note.get('title', 'Untitled')} (Created: {date_str}"
                if time_str:
                    response += f" at {time_str}"
                response += ")\n"
                response += f"   Content: {note.get('content', '')[:100]}"
                if len(note.get("content", "")) > 100:
                    response += "..."
                response += "\n\n"
            response += "Let me know if you need more details about any specific note!"
            return response

    # Specific account questions
    elif account_data and any(
        keyword in query_lower for keyword in ["points", "tier", "loyalty", "rewards"]
    ):
        account = account_data[0]
        if "points" in query_lower and "tier" in query_lower:
            points_needed = account.get("points_to_next_tier", 0)
            next_tier = account.get("next_tier", "N/A")
            return (
                f"You need {points_needed} more points to reach "
                f"the next tier ({next_tier.title()})."
            )
        elif "how many" in query_lower and (
            "tier" in query_lower or "points" in query_lower
        ):
            points_needed = account.get("points_to_next_tier", 0)
            next_tier = account.get("next_tier", "N/A")
            return (
                f"You need {points_needed} more points to reach "
                f"the next tier ({next_tier.title()})."
            )
        elif "balance" in query_lower:
            current_balance = account.get("current_balance", 0)
            pending_balance = account.get("pending_balance", 0)
            return (
                f"Your current loyalty points balance is {current_balance} "
                f"(with {pending_balance} pending)."
            )
        else:
            return (
                "Based on your account information, I can help you with specific "
                "questions about your loyalty status, rewards, or account details."
            )

    # Default response
    else:
        if account_data or facility_data or notes_data:
            return (
                "I've gathered the available information. How can I help you with "
                "your account, facilities, or notes?"
            )
        else:
            return (
                "I apologize, but I couldn't process your request. Please try "
                "asking about your account, facilities, or notes."
            )


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

    # Get the tools (no need for determine_response_structure tool anymore)
    tools = [fetch_account_details, fetch_facility_details, save_notes, fetch_notes]

    # Get the prompt template
    from app.prompts import get_agent_prompt

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

    # Create message with context
    message_content = f"""User Query: {text}

Context:
- Account ID: {account_id} (use this account_id when calling fetch_account_details tool)
- User ID: {user_id} (use this user_id when calling fetch_notes tool)
{f'- Facility ID: {facility_id} (use this facility_id when calling fetch_facility_details tool)' if facility_id else ''}  # noqa: E501

Please help the user with their request. Use the available tools with the IDs provided above to fetch the necessary data."""

    # Prepare input for the agent
    human_message = HumanMessage(content=message_content)
    agent_input = {"messages": [human_message]}

    # Save the human message to conversation memory
    conv_memory.add_message(final_conversation_id, human_message)

    # Run the agent with conversation memory
    try:
        result = agent.invoke(
            agent_input, config={"configurable": {"thread_id": final_conversation_id}}
        )

        # Extract data from the result
        account_data = []
        facility_data = []
        notes_data = []
        response_content = ""
        tools_called = set()

        if isinstance(result, dict) and "messages" in result:
            messages = result["messages"]

            # Extract tool results and track which tools were called
            for msg in messages:
                # Track tool calls
                if hasattr(msg, "name") and msg.name:
                    tools_called.add(msg.name)

                if hasattr(msg, "content") and isinstance(msg.content, str):
                    try:
                        # Try to parse as JSON to extract structured data
                        tool_result = json.loads(msg.content)
                        if isinstance(tool_result, dict):
                            if "account_overview" in tool_result:
                                account_data = tool_result.get("account_overview", [])
                            if "facility_overview" in tool_result:
                                facility_data = tool_result.get("facility_overview", [])
                            if "note_overview" in tool_result:
                                notes_data = tool_result.get("note_overview", [])
                    except json.JSONDecodeError:
                        # If not JSON, check if it's a natural language response
                        if not response_content and len(msg.content) > 10:
                            response_content = msg.content

            # Get the last AI message (the final response) - skip context messages
            for msg in reversed(messages):
                if (
                    hasattr(msg, "content")
                    and msg.content
                    and not response_content
                    and not msg.content.startswith("User Query:")
                    and not msg.content.startswith("Context:")
                    and not msg.content.startswith("Please help the user")
                    and len(msg.content) > 20
                ):
                    response_content = msg.content
                    break

            # If no proper response found or response is just context,
            # generate one based on the data
            if (
                not response_content
                or response_content.startswith("User Query:")
                or response_content.startswith("Context:")
                or response_content.startswith("Please help the user")
            ):
                response_content = _generate_response_from_data(
                    text, account_data, facility_data, notes_data
                )

        else:
            response_content = str(result)

        # Intelligently determine card_key based on which tools were called
        # and what data was fetched
        card_key = _determine_card_key(
            text, tools_called, account_data, facility_data, notes_data
        )

        # Save the AI response to conversation memory
        ai_message = AIMessage(content=response_content)
        conv_memory.add_message(final_conversation_id, ai_message)

        # Return structured response
        return AgentResponse(
            conversation_id=final_conversation_id,
            final_response=response_content,
            card_key=card_key,
            account_overview=account_data,
            facility_overview=facility_data if facility_data else None,
            note_overview=notes_data,
            rewards_overview=None,
            order_overview=None,
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
