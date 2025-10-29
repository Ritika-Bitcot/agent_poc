"""Agent factory using LangGraph create_react_agent."""

import json
from typing import Any, Optional

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

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


def create_agent(openai_api_key: str, model_name: str = "gpt-4o-mini") -> Any:
    """
    Create the agent using LangGraph's StateGraph.

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

    # Bind tools to the LLM
    llm_with_tools = llm.bind_tools(tools)

    # Define the agent function
    def agent_node(state):
        messages = state["messages"]
        # Check if system message is already present
        has_system = any(
            msg.type == "system" for msg in messages if hasattr(msg, "type")
        )

        # Add system prompt if not present
        if not has_system:
            formatted_prompt = prompt.format_messages()
            all_messages = formatted_prompt + messages
        else:
            all_messages = messages

        response = llm_with_tools.invoke(all_messages)
        return {"messages": [response]}

    # Define the tool execution function
    def tool_node(state):
        messages = state["messages"]
        last_message = messages[-1]

        # Execute tools if the last message has tool calls
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            tool_results = []
            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                # Find and execute the tool
                for tool in tools:
                    if tool.name == tool_name:
                        try:
                            result = tool.invoke(tool_args)
                            # Convert result to JSON string if it's a dict
                            if isinstance(result, dict):
                                import json

                                result_str = json.dumps(result)
                            else:
                                result_str = str(result)
                            tool_results.append(
                                {
                                    "tool_call_id": tool_call["id"],
                                    "content": result_str,
                                }
                            )
                        except Exception as e:
                            tool_results.append(
                                {
                                    "tool_call_id": tool_call["id"],
                                    "content": f"Error executing tool: {str(e)}",
                                }
                            )
                        break

            # Add tool results to messages
            from langchain_core.messages import ToolMessage

            tool_messages = [
                ToolMessage(
                    content=result["content"], tool_call_id=result["tool_call_id"]
                )
                for result in tool_results
            ]
            return {"messages": tool_messages}

        return {"messages": []}

    # Define routing function to determine if we should continue or end
    def should_continue(state):
        messages = state["messages"]
        last_message = messages[-1]

        # If the last message has tool calls, route to tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        # Otherwise, we're done
        return END

    # Create the graph
    from typing import Annotated, TypedDict

    class AgentState(TypedDict):
        messages: Annotated[list, add_messages]

    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)

    # Add conditional edges
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")  # Loop back to agent after tools

    # Set entry point
    workflow.set_entry_point("agent")

    # Compile the graph
    memory = MemorySaver()
    agent = workflow.compile(checkpointer=memory)

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
        _agent = create_agent(openai_api_key)
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

    # Prepare the input for the agent
    # create_react_agent expects dict with "messages" key

    # Create message with context
    message_content = f"""User Query: {text}

Context:
- Account ID: {account_id} (use this account_id when calling
  fetch_account_details tool)
- User ID: {user_id} (use this user_id when calling fetch_notes tool)
{f'- Facility ID: {facility_id} (use this facility_id when calling '
 f'fetch_facility_details tool)' if facility_id else ''}

Please help the user with their request. Use the available tools with
the IDs provided above."""

    # StateGraph expects input as dict with "messages" key
    # System prompt will be added by agent_node if not present
    agent_input = {"messages": [HumanMessage(content=message_content)]}

    # Run the agent
    try:
        result = agent.invoke(
            agent_input, config={"configurable": {"thread_id": final_conversation_id}}
        )

        # Extract tool results and response from messages
        account_data = None
        facility_data = None
        notes_data = []
        response_content = ""

        if isinstance(result, dict) and "messages" in result:
            messages = result["messages"]

            # Extract tool results from messages
            from langchain_core.messages import ToolMessage

            for msg in messages:
                # Check if this is a tool result (ToolMessage)
                if isinstance(msg, ToolMessage):
                    # Tool results are stored as content
                    tool_result = msg.content
                    # Try to parse as JSON if it's a string
                    if isinstance(tool_result, str):
                        try:
                            tool_result = json.loads(tool_result)
                        except json.JSONDecodeError:
                            pass

                    if isinstance(tool_result, dict):
                        if "account_overview" in tool_result:
                            # Extract facilities before removing them from account data
                            account_list = tool_result.get("account_overview", [])
                            # Collect facility IDs from account data
                            facility_ids_from_account = []
                            for acc in account_list:
                                if "facilities" in acc and isinstance(
                                    acc["facilities"], list
                                ):
                                    for facility in acc["facilities"]:
                                        if "id" in facility:
                                            facility_ids_from_account.append(
                                                facility["id"]
                                            )

                            # Remove 'facilities' field from each account
                            # as it's not in AccountOverview model
                            account_data = [
                                {k: v for k, v in acc.items() if k != "facilities"}
                                for acc in account_list
                            ]

                            # If we have facility IDs from account,
                            # fetch full facility details
                            if facility_ids_from_account and not facility_data:
                                from app.data import get_data_loader

                                data_loader = get_data_loader()
                                facilities_from_account = []
                                for fac_id in facility_ids_from_account:
                                    fac_data = data_loader.get_facility_by_id(fac_id)
                                    if fac_data:
                                        facilities_from_account.append(fac_data)
                                if facilities_from_account:
                                    facility_data = facilities_from_account
                        elif "facility_overview" in tool_result:
                            facility_data = tool_result.get("facility_overview", [])
                        elif "note_overview" in tool_result:
                            notes_data = tool_result.get("note_overview", [])

            # Get the last AI message (the final response)
            for msg in reversed(messages):
                # Skip tool messages and get the last AI response
                if not isinstance(msg, ToolMessage):
                    if hasattr(msg, "content") and msg.content:
                        response_content = msg.content
                        break

            if not response_content:
                response_content = "I apologize, but I couldn't process your request."
        else:
            response_content = str(result)

        # Determine card_key based on user input
        # Only use specific card_keys for explicit overview requests
        # All follow-up questions, greetings, and specific queries use "other"
        text_lower = text.lower().strip()

        # Check for explicit overview requests (must be exact phrases)
        if text_lower in ["show account overview", "account overview"] or (
            "show" in text_lower
            and "account" in text_lower
            and "overview" in text_lower
        ):
            card_key = "account_overview"
        elif text_lower in ["show facility overview", "facility overview"] or (
            "show" in text_lower
            and "facility" in text_lower
            and "overview" in text_lower
        ):
            card_key = "facility_overview"
        elif text_lower in ["show notes", "show my notes", "notes"] or (
            "show" in text_lower and "notes" in text_lower
        ):
            card_key = "notes_overview"
        else:
            # All follow-up questions, greetings, and specific queries use "other"
            card_key = "other"

        # Fetch data directly if tool wasn't called and we need it
        from app.data import get_data_loader

        data_loader = get_data_loader()

        if card_key == "account_overview" and not account_data:
            account_fetched = data_loader.get_account_by_id(account_id)
            if account_fetched:
                # Extract facilities before removing them
                facility_ids_from_account = []
                if "facilities" in account_fetched and isinstance(
                    account_fetched["facilities"], list
                ):
                    for facility in account_fetched["facilities"]:
                        if "id" in facility:
                            facility_ids_from_account.append(facility["id"])

                # Remove 'facilities' field as it's not part of AccountOverview model
                account_fetched = {
                    k: v for k, v in account_fetched.items() if k != "facilities"
                }
                account_data = [account_fetched]

                # Fetch full facility details if we have facility IDs
                if facility_ids_from_account and not facility_data:
                    facilities_from_account = []
                    for fac_id in facility_ids_from_account:
                        fac_data = data_loader.get_facility_by_id(fac_id)
                        if fac_data:
                            facilities_from_account.append(fac_data)
                    if facilities_from_account:
                        facility_data = facilities_from_account
        elif card_key == "facility_overview" and not facility_data:
            if facility_id:
                # Fetch specific facility
                facility_fetched = data_loader.get_facility_by_id(facility_id)
                if facility_fetched:
                    facility_data = [facility_fetched]
            else:
                # Fetch all facilities for the account
                facilities_fetched = data_loader.get_facilities_by_account_id(
                    account_id
                )
                facility_data = facilities_fetched
        elif card_key == "notes_overview" and not notes_data:
            notes_fetched = data_loader.get_notes_by_user_id(user_id)
            if notes_fetched:
                # Limit to last 5 notes as per requirements
                notes_fetched.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                notes_data = notes_fetched[:5]

        # Format response based on tool results
        if facility_data and card_key == "facility_overview":
            if len(facility_data) == 1:
                # Single facility
                facility = facility_data[0]
                account_name = facility.get("account_name", "N/A")
                account_id_val = facility.get("account_id", "N/A")
                addr_line1 = facility.get("shipping_address_line1", "N/A")
                addr_city = facility.get("shipping_address_city", "N/A")
                addr_state = facility.get("shipping_address_state", "N/A")
                addr_zip = facility.get("shipping_address_zip", "N/A")
                license_num = facility.get("medical_license_number", "N/A")
                license_status = facility.get("medical_license_status", "N/A")
                license_exp_date = facility.get(
                    "medical_license_expiration_date", "N/A"
                )
                owner_first = facility.get("medical_license_owner_first_name", "N/A")
                owner_last = facility.get("medical_license_owner_last_name", "N/A")
                agreement_status = facility.get("agreement_status", "N/A")
                agreement_type = facility.get("agreement_type", "N/A")
                medical_license_line = (
                    f"{license_num} ({license_status}, " f"expires {license_exp_date})"
                )
                final_response = f"""Here is a summary of your facility:

        - Facility Name: {facility.get('name', 'N/A')}
        - Status: {facility.get('status', 'N/A')}
        - Facility ID: {facility.get('id', 'N/A')}
        - Account: {account_name} ({account_id_val})
        - Shipping Address: {addr_line1}, {addr_city}, {addr_state} {addr_zip}
        - Medical License: {medical_license_line}
        - License Owner: {owner_first} {owner_last}
        - Agreement Status: {agreement_status} ({agreement_type})
        - Agreement Signed: {facility.get('agreement_signed_at', 'N/A')}

        Let me know if you need more detailed information or have other questions!"""
            else:
                # Multiple facilities
                final_response = (
                    f"Here are all your facilities ({len(facility_data)} total):\n\n"
                )
                for i, facility in enumerate(facility_data, 1):
                    final_response += (
                        f"{i}. {facility.get('name', 'N/A')} "
                        f"({facility.get('id', 'N/A')}) - "
                        f"Status: {facility.get('status', 'N/A')}\n"
                    )
                final_response += (
                    "\nLet me know if you need more detailed information "
                    "about any specific facility!"
                )
        elif account_data and card_key == "account_overview":
            account = account_data[0] if account_data else {}
            # Format address exactly as expected:
            # "100 WYCLIFFE, IRVINE, CA 92602-1206"
            address_line1 = account.get("address_line1", "")
            address_city = account.get("address_city", "")
            address_state = account.get("address_state", "")
            address_postal = account.get("address_postal_code", "")

            address_parts = [address_line1, address_city, address_state]
            address = ", ".join(filter(None, address_parts))
            if address_postal:
                address += f" {address_postal}"

            final_response = f"""Here is a summary of your account:

        - Account Name: {account.get('name', 'N/A')}
        - Status: {account.get('status', 'N/A')}
        - Account ID: {account.get('account_id', 'N/A')}
        - Address: {address}
        - Pricing Model: {account.get('pricing_model', 'N/A')}

        Loyalty & Rewards:
        - Current Loyalty Tier: {account.get('current_tier', 'N/A')} (
          next tier: {account.get('next_tier', 'N/A')}, {
          account.get('points_to_next_tier', 0)} points needed)
        - Loyalty Points Balance: {account.get('current_balance', 0)} (
          pending: {account.get('pending_balance', 0)})
        - Free Vials Available: {
          account.get('free_vials_available', 0)}
        - Rewards Redeemed Toward Next Free Vial: {
          account.get('rewards_redeemed_towards_next_free_vial', 0)} ({
          account.get('rewards_required_for_next_free_vial', 0)} needed
          for next free vial)

        Other Details:
        - Evolux Level: {account.get('evolux_level', 'N/A')}
        - Reward Program Opt-in Status: {account.get('rewards_status', 'N/A')}

        Let me know if you need more detailed information or have other questions!"""
        elif card_key == "notes_overview":
            # Format notes response
            if not notes_data:
                final_response = "You don't have any notes saved yet."
            else:
                final_response = f"Here are your notes ({len(notes_data)} total):\n\n"
                for i, note in enumerate(notes_data, 1):
                    # Parse date if needed
                    created_at = note.get("created_at", "")
                    date_str = (
                        created_at.split("T")[0] if "T" in created_at else created_at
                    )
                    time_str = (
                        created_at.split("T")[1].split(".")[0]
                        if "T" in created_at
                        else ""
                    )

                    final_response += (
                        f"{i}. {note.get('title', 'Untitled')} (Created: {date_str}"
                    )
                    if time_str:
                        final_response += f" at {time_str}"
                    final_response += ")\n"
                    final_response += f"   Content: {note.get('content', '')[:100]}"
                    if len(note.get("content", "")) > 100:
                        final_response += "..."
                    final_response += "\n\n"
                final_response += (
                    "Let me know if you need more details about any specific note!"
                )
        elif (
            card_key == "other"
            and "how many" in text_lower
            and ("tier" in text_lower or "points" in text_lower)
        ):
            # Handle tier question - need to fetch account data first
            # if not already fetched
            if not account_data:
                # Try to fetch account data for the question
                from app.data import get_data_loader

                data_loader = get_data_loader()
                account_fetched = data_loader.get_account_by_id(account_id)
                if account_fetched:
                    # Remove 'facilities' field as it's not part of
                    # AccountOverview model
                    account_fetched = {
                        k: v for k, v in account_fetched.items() if k != "facilities"
                    }
                    account_data = [account_fetched]

            if account_data:
                account = account_data[0] if account_data else {}
                points_needed = account.get("points_to_next_tier", 0)
                next_tier = account.get("next_tier", "N/A")
                final_response = (
                    f"You need {points_needed} more points to reach "
                    f"the next tier ({next_tier.title()})."
                )
            else:
                final_response = (
                    response_content
                    if response_content
                    else (
                        "I couldn't find account information to answer "
                        "your question about loyalty tiers."
                    )
                )
        else:
            final_response = response_content

        # For "other" card_key, don't include account_overview even if
        # data was fetched
        # Include facility_overview when card_key is "account_overview" or
        # "facility_overview"
        return AgentResponse(
            conversation_id=final_conversation_id,
            final_response=final_response,
            card_key=card_key,
            account_overview=account_data if card_key == "account_overview" else [],
            facility_overview=(
                facility_data
                if (card_key == "facility_overview" or card_key == "account_overview")
                else None
            ),
            note_overview=notes_data if card_key == "notes_overview" else [],
            rewards_overview=None,
            order_overview=None,
        )

    except Exception as e:
        # Error fallback
        return AgentResponse(
            conversation_id=final_conversation_id,
            final_response=(
                f"I apologize, but I encountered an error processing "
                f"your request: {str(e)}"
            ),
            card_key="other",
            account_overview=[],
            facility_overview=None,
            note_overview=[],
            rewards_overview=None,
            order_overview=None,
        )
