# Test-API Documentation

A FastAPI-based RAG (Retrieval Augmented Generation) API that uses LightRAG for document processing and querying, with Supabase for history storage.

## Base URL

```
http://localhost:8000
```

## Authentication

This API requires JWT token authentication for all endpoints. Include the JWT token in the `Authorization` header using the Bearer scheme:

```
Authorization: Bearer <your_jwt_token>
```

The JWT token must be obtained using a valid API key. The token is valid for 30 days and contains the API key as its subject.

## API Endpoints

### Authentication

#### Get JWT Token

- **Endpoint**: `/auth/token`
- **Method**: GET
- **Description**: Get a JWT token using a valid API key.
- **Headers**:
  - `Authorization`: Bearer your.jwt.token
- **Response**:
  ```json
  {
    "access_token": "your.jwt.token",
    "token_type": "bearer"
  }
  ```

#### Verify Authentication

- **Endpoint**: `/auth/verify`
- **Method**: GET
- **Description**: Verify that the request is authenticated using a JWT token.
- **Headers**:
  - `Authorization`: Bearer your.jwt.token
- **Response**: Empty response if authentication is successful, 401 if authentication fails.

### Document Ingestion

#### Ingest Document

- **Endpoint**: `/ingest/file`
- **Method**: POST
- **Description**: Ingest a document file (PDF, DOCX, TXT) into the RAG system.
- **Headers**:
  - `Authorization`: Bearer your.jwt.token
- **Form Data**:
  - `file`: The file to upload
- **Response**:
  ```json
  {
    "type": "document",
    "file_name": "your_file_name",
    "file_type": "pdf|docx|txt",
    "query": "List my resume?"
  }
  ```

#### Ingest Website

- **Endpoint**: `/ingest/url`
- **Method**: POST
- **Description**: Ingest content from a website URL into the RAG system.
- **Headers**:
  - `Authorization`: Bearer your.jwt.token
- **Form Data**:
  - `url`: The website URL to ingest
- **Response**:
  ```json
  {
    "type": "website",
    "url": "your_url",
    "query": "List my resume?"
  }
  ```

### Query Endpoints

#### Query RAG

- **Endpoint**: `/query`
- **Method**: GET
- **Description**: Query the RAG system with a question.
- **Headers**:
  - `Authorization`: Bearer your.jwt.token
- **Query Parameters**:
  - `query`: The question to ask
- **Response**:
  ```json
  {
    "response": "your_response"
  }
  ```

#### Stream Query

- **Endpoint**: `/stream-query`
- **Method**: GET
- **Description**: Stream query results from the RAG system.
- **Headers**:
  - `Authorization`: Bearer your.jwt.token
- **Query Parameters**:
  - `query`: The question to ask
- **Response**: Stream of text chunks
## Chat History

#### Get Chat History

- **Endpoint**: `/embed/{embed_id}/{session_id}`
- **Method**: GET
- **Description**: Retrieve chat history for a specific session.
- **Path Parameters**:
  - `embed_id`: The ID of the embed configuration
  - `session_id`: The specific session ID
- **Headers**:
  - `Authorization`: Bearer your.jwt.token
- **Response**:
  ```json
  {
    "history": [
      {
        "role": "user|assistant",
        "content": "message_content",
        "timestamp": "message_timestamp"
      }
    ]
  }
  ```

#### Delete Chat History

- **Endpoint**: `/embed/{embed_id}/{session_id}`
- **Method**: DELETE
- **Description**: Delete chat history for a specific session.
- **Path Parameters**:
  - `embed_id`: The ID of the embed configuration
  - `session_id`: The specific session ID to delete
- **Headers**:
  - `Authorization`: Bearer your.jwt.token
- **Response**: Empty response with status code 200

## Stream Chat

#### Stream Chat with RAG

- **Endpoint**: `/embed/{embed_id}/stream-chat`
- **Method**: POST
- **Description**: Stream chat with the RAG system.
- **Path Parameters**:
  - `embed_id`: The ID of the embed configuration
- **Headers**:
  - `Authorization`: Bearer your.jwt.token
- **Request Body**:
  ```json
  {
    "session_id": "your_session_id",
    "message": "your_message"
  }
  ```
- **Response**: Server-sent events stream with chunks containing:
  ```json
  {
    "uuid": "message_uuid",
    "type": "textResponse|error",
    "textResponse": "message_content",
    "sources": [],
    "close": true|false,
    "error": true|false
  }
  ```

## Status Codes

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication failed
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

## Error Responses

All endpoints may return error responses in the following format:

```json
{
    "error": {
        "code": "error_code",
        "message": "error_message"
    }
}
```

## Security

- All endpoints require authentication (either API key or JWT token)
- Sensitive data is protected using JWT tokens
- API keys should be kept secure and not exposed in client-side code
- JWT tokens have a configurable expiration time

## Rate Limiting

- Rate limiting is applied to prevent abuse
- Limits are based on API key
- Exceeding limits will result in 429 Too Many Requests response

## API Versioning

- API version is included in the base URL
- Breaking changes will be introduced in major version updates
- Non-breaking changes will be introduced in minor version updates

## Examples

### Example 1: Get JWT Token

```bash
# Using API key in header
curl -X GET "http://localhost:8000/auth/token" \
-H "X-API-Key: your_api_key"

# Using API key as query parameter
curl -X GET "http://localhost:8000/auth/token?api_key=your_api_key"
```

### Example 2: Ingest Document

```bash
curl -X POST "http://localhost:8000/ingest/file" \
-H "Authorization: Bearer your_jwt_token" \
-F "file=@path/to/your/document.pdf"
```

### Example 3: Query RAG

```bash
curl -X GET "http://localhost:8000/query?query=your_question" \
-H "Authorization: Bearer your_jwt_token"
```

## API Usage Guidelines

1. Always include the appropriate authentication header
2. Use the correct content type for multipart/form-data requests
3. Handle streaming responses appropriately
4. Implement proper error handling
5. Respect rate limits
6. Keep API keys and JWT tokens secure

## Support

For support, please contact our support team at support@example.com

## API Usage Guidelines

1. Always include the appropriate authentication header
2. Use the correct content type for multipart/form-data requests
3. Handle streaming responses appropriately
4. Implement proper error handling
5. Respect rate limits
6. Keep API keys and JWT tokens secure

## Support

For support, please contact our support team at support@example.com
## Data Models

### StreamChatRequest

```json
{
  "session_id": "string",
  "message": "string"
  // Optional: "username": "string", "prompt": "string", "model": "string", "temperature": number
}
```

### ChatMessage

```json
{
  "role": "user|assistant",
  "content": "string",
  "uuid": "string"
}
```

### HistoryResponse

```json
{
  "history": [
    {
      "role": "string",
      "content": "string",
      "uuid": "string"
    }
  ]
}
```

## Environment Variables

The API requires the following environment variables:

- `SUPABASE_URL`: URL for the Supabase instance
- `SUPABASE_KEY`: API key for Supabase
- `PORT`: Port for the server (default: 8000)
- `HOST`: Host for the server (default: 127.0.0.1)
- `GEMINI_API_KEY`: API key for Google Gemini
- `API_KEYS`: Comma-separated list of valid API keys for JWT token generation
- `JWT_SECRET_KEY`: Secret key for signing JWT tokens
- `JWT_ALGORITHM`: Algorithm used for JWTs (default: HS256)
- `TOKEN_EXPIRE_DAYS`: Number of days until JWT token expires (default: 30)