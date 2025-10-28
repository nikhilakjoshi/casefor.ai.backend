# CaseforAI Backend

FastAPI application for document processing and vector storage using LlamaIndex, Pinecone, and Gemini embeddings.

## Setup

### 1. Environment Setup

```bash
# Create conda environment
conda env create -f environment.yml

# Or create manually
conda create -n caseforai-backend python=3.12 -y
conda activate caseforai-backend
pip install -r requirements.txt
```

### 2. Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your API keys:
- `PINECONE_API_KEY`: Your Pinecone API key
- `GOOGLE_API_KEY`: Your Google API key for Gemini embeddings

### 3. Pinecone Setup

Create a Pinecone index named `caseforai-embeddings` in your Pinecone dashboard.

## Usage

### Start Server

```bash
conda activate caseforai-backend
uvicorn main:app --reload
```

Server runs on `http://localhost:8000`

### API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `POST /upload` - Upload and process documents

### Supported File Types

- PDF (`.pdf`)
- Word Documents (`.docx`)
- Text Files (`.txt`)
- Markdown (`.md`)
- Excel Files (`.xlsx`)

### Example Upload

```bash
curl -X POST "http://localhost:8000/upload" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@document.pdf"
```

## Features

- Document parsing with LlamaIndex
- Vector embeddings using Gemini embeddings-001
- Vector storage in Pinecone
- Automatic chunking (1024 tokens default)
- File metadata tracking