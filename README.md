# test-api

This FastAPI application uses LightRAG for RAG capabilities and Supabase for data storage.

## Project Components
- **Framework**: FastAPI with Uvicorn server
- **Database**: Supabase
- **AI/ML**: LightRAG for RAG capabilities, using Google Gemini API
- **Data Storage**: Local file storage for RAG data (will need adaptation for cloud deployment)

## Docker Deployment

### Prerequisites
- Docker and Docker Compose installed
- Environment variables configured in `.env` file

### Steps to Deploy with Docker

1. **Create a `.env` file based on the example**
   ```
   cp .env.example .env
   ```
   Then fill in the required environment variables:
   - SUPABASE_URL
   - SUPABASE_KEY
   - GEMINI_API_KEY
   - PORT (optional, defaults to 8000)
   - HOST (optional, defaults to 0.0.0.0)
   - JWT_SECRET_KEY
   - JWT_ALGORITHM
   - TOKEN_EXPIRE_DAYS
   - API_KEYS

2. **Build and start the Docker container**
   ```
   docker-compose up -d
   ```

3. **View logs**
   ```
   docker-compose logs -f
   ```

4. **Stop the container**
   ```
   docker-compose down
   ```

## Important Notes
- The application uses local file storage for RAG data. For production, consider using a persistent storage solution.
- Make sure Supabase is properly configured and accessible from your deployment environment.
- The Google Gemini API key needs to be set in the environment variables.
- When using Docker, the `db` directory is mounted as a volume to persist RAG data between container restarts.
