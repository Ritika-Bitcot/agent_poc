# Production Deployment Guide

## Quick Start with Docker

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd agent_poc
   cp env.example .env
   # Edit .env with your OpenAI API key
   ```

2. **Deploy with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

3. **Access the API:**
   - API: http://localhost:8000
   - Health Check: http://localhost:8000/health
   - API Docs: http://localhost:8000/docs

## Environment Variables

Create a `.env` file with the following variables:

```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional
MODEL_NAME=gpt-4o-mini
DEBUG=false
HOST=0.0.0.0
PORT=8000
WORKERS=1
RELOAD=false

# Database (for Docker Compose)
DATABASE_URL=postgresql://postgres:password@db:5432/agent_poc_db
```

## Manual Deployment

### Prerequisites
- Python 3.11+
- PostgreSQL (optional, for conversation memory)
- OpenAI API key

### Steps

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export OPENAI_API_KEY="your_api_key_here"
   ```

3. **Run the application:**
   ```bash
   python main.py
   ```

## Production Considerations

### Security
- Set `DEBUG=false` in production
- Use environment variables for sensitive data
- Consider using a reverse proxy (nginx) for SSL termination
- Implement rate limiting and authentication as needed

### Performance
- Adjust `WORKERS` based on your server capacity
- Use a production ASGI server like Gunicorn with Uvicorn workers
- Consider database connection pooling for high traffic

### Monitoring
- Set up health checks on `/health` endpoint
- Monitor application logs
- Consider adding metrics collection (Prometheus, etc.)

### Database
- For production, use a managed PostgreSQL service
- Set up database backups
- Consider read replicas for high availability

## Scaling

### Horizontal Scaling
- Use a load balancer (nginx, HAProxy)
- Deploy multiple instances behind the load balancer
- Use shared database for conversation memory

### Vertical Scaling
- Increase `WORKERS` count
- Use more powerful server instances
- Optimize database queries

## Health Checks

The application provides a health check endpoint at `/health` that returns:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## API Documentation

Once deployed, access the interactive API documentation at:
- Swagger UI: `http://your-domain/docs`
- ReDoc: `http://your-domain/redoc`
