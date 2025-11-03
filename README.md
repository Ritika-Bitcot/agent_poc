# Agent POC - LangGraph + FastAPI

A single-agent architecture built with LangGraph and FastAPI that supports multi-turn conversations with short-term memory.

## Features

- **Single Agent Architecture**: Uses LangChain's `create_agent` for agent creation
- **Multi-turn Conversations**: Maintains conversation history and context using PostgreSQL
- **Structured Output**: Returns structured responses with Pydantic models
- **Modular Design**: Clean separation of concerns across different modules
- **FastAPI Integration**: RESTful API with automatic documentation
- **Memory Management**: PostgreSQL-based conversation memory
- **Error Handling**: Centralized error handling with consistent response format

## Project Structure

```
agent_poc/
├── app/
│   ├── agent/           # Agent creation and management
│   ├── api/             # FastAPI endpoints
│   ├── memory/          # Conversation memory
│   ├── models/          # Pydantic models
│   ├── prompts/         # Prompt templates
│   └── tools/           # Agent tools
├── tests/               # Test files
├── main.py             # Application entry point
├── requirements.txt    # Dependencies
└── README.md          # This file
```

## Tools Available

1. **fetch_account_details** - Retrieve account related information
2. **fetch_facility_details** - Retrieve facility related information  
3. **save_notes** - Save MOM or notes given by user
4. **fetch_notes** - Retrieve notes based on user_id/date/last 5 notes

## Response Format

The agent returns structured responses with:

- `conversation_id`: Unique conversation identifier
- `final_response`: Human-friendly natural language response
- `card_key`: UI card type (`account_overview`, `facility_overview`, `notes_overview`, `other`)
- `account_overview`: Account details array
- `facility_overview`: Facility details array
- `note_overview`: Notes array
- `rewards_overview`: Rewards information
- `order_overview`: Order information

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up PostgreSQL Database**:
   ```bash
   # Install PostgreSQL (Ubuntu/Debian)
   sudo apt-get install postgresql postgresql-contrib
   
   # Start PostgreSQL service
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   
   # Create database and user
   sudo -u postgres createdb agent_poc_db
   sudo -u postgres createuser --interactive
   # Follow prompts to create a user with password
   
   # Grant privileges
   sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE agent_poc_db TO your_username;"
   ```

3. **Set Environment Variables**:
   ```bash
   cp env.example .env
   # Edit .env with your OpenAI API key and database credentials
   ```

4. **Run the Application**:
   ```bash
   python main.py
   ```

   Or with uvicorn directly:
   ```bash
   uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## API Endpoints

- `GET /` - Root endpoint
- `POST /chat` - Chat with the agent (main endpoint)

## Data Structure

The application now uses JSON files for mock data storage:

- `app/data/account_data.json` - Account information
- `app/data/facility_data.json` - Facility information  
- `app/data/notes_data.json` - User notes data

All tools now read from and write to these JSON files instead of using hardcoded data.

## Example Usage

### API Request Format

The `/chat` endpoint accepts the following request format:

**Account Overview Request:**
```json
{
  "text": "show account overview",
  "user_id": "kaushal.sethia.c@evolus.com",
  "title": "sample",
  "account_id": "A-011977763"
}
```

**Fetch Account Details:**
```json
{
  "text": "fetch account details",
  "user_id": "3867",
  "title": "postman_test",
  "account_id": "A-011977763"
}
```

**Fetch Facility Details:**
```json
{
  "text": "fetch facility details",
  "user_id": "3867",
  "title": "postman_test",
  "account_id": "A-011977763",
  "facility_id": "F-013203268"
}
```

**Follow-up Question:**
```json
{
  "text": "how many points do I need to go to next tier",
  "user_id": "kaushal.sethia.c@evolus.com", 
  "title": "sample",
  "account_id": "A-011977763",
  "conversation_id": "c625fbc7-cc93-4a7e-841b-180872a9420a"
}
```

## Development

For development, install additional dependencies:

```bash
pip install -r requirements-dev.txt
```

Set up pre-commit hooks:

```bash
pre-commit install
```

## Postman Collection

A Postman collection is provided (`postman_collection.json`) with pre-configured requests for easy testing. Import this collection into Postman to test all endpoints.

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Configuration

The application can be configured through environment variables:

### Application Settings
- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `MODEL_NAME`: Model to use (default: gpt-4o-mini)
- `DEBUG`: Enable debug mode (default: True)

### Database Settings
- `DATABASE_URL`: Complete PostgreSQL connection string (optional)
- `DB_HOST`: Database host (default: localhost)
- `DB_PORT`: Database port (default: 5432)
- `DB_NAME`: Database name (default: agent_poc_db)
- `DB_USER`: Database username (default: username)
- `DB_PASSWORD`: Database password (default: password)

If `DATABASE_URL` is provided, it will be used instead of the individual database settings.

## Development

The codebase follows a modular architecture with SOLID principles:

- **Tools**: Implemented as LangChain tools with proper schemas
- **Prompts**: Comprehensive prompts with detailed instructions and examples
- **Memory**: PostgreSQL-based conversation memory with automatic cleanup
- **Models**: Pydantic models for request/response validation and type safety
- **API**: FastAPI with centralized error handling and consistent responses
- **Agent Factory**: Refactored with helper functions following single responsibility principle

## Notes

- The application uses mock data for demonstration purposes
- In production, replace mock data with actual API calls
- Configure CORS settings appropriately for your frontend
- Set up proper logging and monitoring for production use
