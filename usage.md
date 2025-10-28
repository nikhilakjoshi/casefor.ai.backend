# CaseforAI Backend API Documentation

## Base URL
```
http://localhost:8000
```

## Overview
The CaseforAI Backend API provides document processing and vector search capabilities using LlamaIndex, Pinecone, and Gemini embeddings. Upload documents to automatically chunk, embed, and store them in a vector database for semantic search.

## Supported File Types
- PDF (`.pdf`)
- Word Documents (`.docx`) 
- Text Files (`.txt`)
- Markdown (`.md`)
- Excel Files (`.xlsx`)

## Authentication
Currently no authentication required. Ensure API keys are configured in `.env`:
- `PINECONE_API_KEY`
- `GOOGLE_API_KEY`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION` (optional, defaults to us-east-1)
- `AWS_S3_BUCKET_NAME` (optional, defaults to caseforai-bucket)

---

## Endpoints

### 1. Root Endpoint
**GET** `/`

Basic health check endpoint.

#### Example Request
```bash
curl -X GET "http://localhost:8000/"
```

#### Response
```json
{
  "message": "CaseforAI Backend API"
}
```

---

### 2. Health Check
**GET** `/health`

System health status.

#### Example Request
```bash
curl -X GET "http://localhost:8000/health"
```

#### Response
```json
{
  "status": "healthy"
}
```

---

### 3. Upload Document
**POST** `/upload`

Upload and process a document. Automatically chunks the document, stores embeddings in Pinecone, and uploads the original file to S3.

#### Parameters
- **file** (form-data, required): Document file to upload

#### Example Request
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

#### Success Response (200)
```json
{
  "message": "File uploaded and processed successfully",
  "filename": "document.pdf",
  "documents_processed": 1,
  "chunks_created": 15,
  "file_type": ".pdf",
  "s3_url": "https://caseforai-bucket.s3.amazonaws.com/documents/2025/10/28/a1b2c3d4_document.pdf"
}
```

#### Partial Success Response (200 - S3 Upload Failed)
```json
{
  "message": "File uploaded and processed successfully",
  "filename": "document.pdf",
  "documents_processed": 1,
  "chunks_created": 15,
  "file_type": ".pdf",
  "s3_url": null,
  "warning": "Document processed successfully but S3 upload failed: [error details]",
  "s3_error": "[detailed S3 error message]"
}
```

#### Error Responses

**400 - Unsupported File Type**
```json
{
  "detail": "Unsupported file type. Supported: ['.pdf', '.docx', '.txt', '.md', '.xlsx']"
}
```

**500 - Processing Error**
```json
{
  "detail": "Error processing file: [error message]"
}
```

---

### 4. Query Documents
**GET** `/query`

Search documents using semantic similarity.

#### Parameters
- **q** (query, required): Search query string
- **limit** (query, optional): Number of results to return (1-50, default: 10)

#### Example Request
```bash
curl -X GET "http://localhost:8000/query?q=machine%20learning&limit=5"
```

#### Success Response (200)
```json
{
  "query": "machine learning",
  "results": [
    {
      "id": "node_123",
      "text": "Machine learning is a subset of artificial intelligence...",
      "score": 0.85,
      "metadata": {
        "filename": "ai_guide.pdf",
        "file_type": ".pdf",
        "upload_timestamp": "2025-10-28T17:30:45.123456"
      }
    }
  ],
  "total_results": 1
}
```

#### Error Response (500)
```json
{
  "detail": "Error querying documents: [error message]"
}
```

---

### 5. List Chunks Information
**GET** `/chunks`

Get information about stored document chunks.

#### Parameters
- **limit** (query, optional): Not currently used (1-1000, default: 100)

#### Example Request
```bash
curl -X GET "http://localhost:8000/chunks"
```

#### Success Response (200)
```json
{
  "total_vectors": 150,
  "index_fullness": 0.0001,
  "namespaces": {
    "": {
      "vector_count": 150
    }
  },
  "note": "Use /query endpoint to search specific chunks"
}
```

---

### 6. Index Statistics
**GET** `/stats`

Get detailed Pinecone index statistics.

#### Example Request
```bash
curl -X GET "http://localhost:8000/stats"
```

#### Success Response (200)
```json
{
  "index_name": "caseforai-embeddings",
  "stats": {
    "total_vector_count": 150,
    "index_fullness": 0.0001,
    "dimension": 768,
    "namespaces": {
      "": {
        "vector_count": 150
      }
    }
  }
}
```

---

## Common Workflows

### 1. Upload and Search Workflow
```bash
# 1. Upload a document
curl -X POST "http://localhost:8000/upload" \
  -F "file=@my_document.pdf"

# 2. Check if upload succeeded
curl -X GET "http://localhost:8000/stats"

# 3. Search the document
curl -X GET "http://localhost:8000/query?q=your%20search%20terms&limit=5"
```

### 2. Monitor System Health
```bash
# Check API health
curl -X GET "http://localhost:8000/health"

# Check vector database stats
curl -X GET "http://localhost:8000/stats"

# Check total chunks
curl -X GET "http://localhost:8000/chunks"
```

---

## Response Schemas

### Upload Response
```typescript
interface UploadResponse {
  message: string;
  filename: string;
  documents_processed: number;
  chunks_created: number;
  file_type: string;
  s3_url: string | null;
  warning?: string;  // Present if S3 upload failed
  s3_error?: string; // Detailed S3 error if upload failed
}
```

### Query Response
```typescript
interface QueryResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
}

interface SearchResult {
  id: string;
  text: string;
  score: number;
  metadata: {
    filename: string;
    file_type: string;
    upload_timestamp: string;
    [key: string]: any;
  };
}
```

### Stats Response
```typescript
interface StatsResponse {
  index_name: string;
  stats: {
    total_vector_count: number;
    index_fullness: number;
    dimension: number;
    namespaces?: {
      [namespace: string]: {
        vector_count: number;
      };
    };
  };
}
```

### Error Response
```typescript
interface ErrorResponse {
  detail: string;
}
```

---

## Integration Notes

### File Upload Considerations
- Maximum file size depends on server configuration
- Processing time varies by document size and complexity
- Large documents are automatically chunked into 1024-token segments with 200-token overlap
- Files are uploaded to S3 after successful Pinecone processing
- S3 URLs are generated with unique paths: `documents/YYYY/MM/DD/uuid_filename.ext`
- S3 upload failure doesn't affect Pinecone processing (graceful degradation)

### Search Behavior
- Uses semantic similarity (not keyword matching)
- Results are ranked by relevance score (0-1, higher is more relevant)
- Search works across all uploaded documents
- Query strings should be natural language

### Error Handling
- All endpoints return JSON responses
- HTTP status codes indicate success (2xx) or failure (4xx/5xx)
- Error messages are in the `detail` field

### Performance
- First upload may be slower due to model initialization
- Subsequent uploads and queries are faster
- Query response time depends on index size and similarity threshold

---

## Development Setup

### Environment Variables
```bash
# .env file
PINECONE_API_KEY=your_pinecone_api_key
GOOGLE_API_KEY=your_google_api_key
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_REGION=us-east-1
AWS_S3_BUCKET_NAME=caseforai-bucket
```

### Running the API
```bash
# Activate conda environment
conda activate caseforai-backend

# Start server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Test basic connectivity
curl http://localhost:8000/health

# Upload test document
curl -X POST http://localhost:8000/upload -F "file=@test.txt"

# Search test
curl "http://localhost:8000/query?q=test&limit=3"
```