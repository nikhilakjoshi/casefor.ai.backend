from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
import tempfile
import os
from pathlib import Path
from typing import List, Optional
import logging
from datetime import datetime

from llama_index.core import Document, VectorStoreIndex, Settings, ServiceContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.gemini import GeminiEmbedding
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.readers.file import (
    PDFReader,
    DocxReader,
    UnstructuredReader,
    MarkdownReader,
)
from pinecone import Pinecone
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError
import uuid

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Validate required environment variables
required_env_vars = ["PINECONE_API_KEY", "GOOGLE_API_KEY", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
for var in required_env_vars:
    if not os.getenv(var):
        raise ValueError(f"Missing required environment variable: {var}")

app = FastAPI(title="CaseforAI Backend", version="1.0.0")

# Initialize embedding model
embed_model = GeminiEmbedding(
    model_name="models/gemini-embedding-001", api_key=os.getenv("GOOGLE_API_KEY")
)
Settings.embed_model = embed_model

# Initialize Pinecone with validation
try:
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    pinecone_index = pc.Index("caseforai-embeddings")

    # Test connection and validate dimensions
    test_stats = pinecone_index.describe_index_stats()
    logger.info(
        f"Connected to Pinecone index. Stats: total_vectors={test_stats.get('total_vector_count', 0)}, dimension={test_stats.get('dimension', 'unknown')}"
    )

    # Test embedding to verify dimensions
    test_embedding = embed_model.get_text_embedding("test")
    embedding_dim = len(test_embedding)
    index_dim = test_stats.get("dimension", 0)

    logger.info(
        f"Embedding model dimension: {embedding_dim}, Pinecone index dimension: {index_dim}"
    )

    if embedding_dim != index_dim and index_dim > 0:
        raise ValueError(
            f"Embedding dimension mismatch: model={embedding_dim}, index={index_dim}"
        )

    logger.info("✅ Embedding dimensions validated successfully")
except Exception as e:
    logger.error(f"Failed to connect to Pinecone: {str(e)}")
    raise e

# Initialize vector store with dimension
vector_store = PineconeVectorStore(
    pinecone_index=pinecone_index, add_sparse_vector=False
)

# Initialize node parser for chunking
node_parser = SentenceSplitter(chunk_size=1024, chunk_overlap=200)
Settings.node_parser = node_parser

# Create global index instance
index = VectorStoreIndex.from_vector_store(vector_store)

# Initialize S3 client
try:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1")  # Default to us-east-1 if not specified
    )
    
    # Test S3 connection
    s3_client.list_buckets()
    logger.info("✅ S3 client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize S3 client: {str(e)}")
    raise e

# S3 bucket name - using the exact env var from .env file
S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME", "caseforai-bucket")

def upload_file_to_s3(file_content: bytes, filename: str, content_type: str) -> str:
    """Upload file to S3 and return the URL"""
    try:
        # Generate unique key with timestamp and UUID
        timestamp = datetime.now().strftime("%Y/%m/%d")
        unique_id = str(uuid.uuid4())[:8]
        file_extension = Path(filename).suffix
        s3_key = f"documents/{timestamp}/{unique_id}_{filename}"
        
        # Upload file to S3
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            ContentType=content_type,
            Metadata={
                'original_filename': filename,
                'upload_timestamp': datetime.now().isoformat()
            }
        )
        
        # Generate URL for the uploaded file
        s3_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
        
        logger.info(f"File uploaded to S3: {s3_url}")
        return s3_url
        
    except ClientError as e:
        logger.error(f"Failed to upload file to S3: {str(e)}")
        raise e

# File readers for different formats
readers = {
    ".pdf": PDFReader(),
    ".docx": DocxReader(),
    ".txt": UnstructuredReader(),
    ".md": MarkdownReader(),
    ".xlsx": UnstructuredReader(),
}


@app.get("/")
async def root():
    return {"message": "CaseforAI Backend API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Validate file type
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in readers:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported: {list(readers.keys())}",
            )

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=file_extension
        ) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            # Read and parse the document
            reader = readers[file_extension]
            documents = reader.load_data(file=tmp_file_path)

            # Add metadata to documents
            for doc in documents:
                doc.metadata["filename"] = file.filename
                doc.metadata["file_type"] = file_extension
                doc.metadata["upload_timestamp"] = datetime.now().isoformat()

            # Parse documents into nodes/chunks
            nodes = node_parser.get_nodes_from_documents(documents)

            logger.info(f"Created {len(nodes)} chunks from {len(documents)} documents")

            # Insert nodes into existing index
            index.insert_nodes(nodes)

            # Verify insertion by checking Pinecone stats
            stats = pinecone_index.describe_index_stats()
            logger.info(f"Pinecone index stats after insertion: {stats}")

            logger.info(
                f"Successfully processed and stored {len(documents)} documents from {file.filename}"
            )
            
            # Upload file to S3 after successful Pinecone processing
            s3_url = None
            s3_error = None
            try:
                s3_url = upload_file_to_s3(content, file.filename, file.content_type or "application/octet-stream")
                logger.info(f"File successfully uploaded to S3: {s3_url}")
            except Exception as s3_e:
                s3_error = str(s3_e)
                logger.error(f"S3 upload failed, but Pinecone processing succeeded: {s3_error}")

            response_content = {
                "message": "File uploaded and processed successfully",
                "filename": file.filename,
                "documents_processed": len(documents),
                "chunks_created": len(nodes),
                "file_type": file_extension,
                "s3_url": s3_url,
            }
            
            # Add warning if S3 upload failed
            if s3_error:
                response_content["warning"] = f"Document processed successfully but S3 upload failed: {s3_error}"
                response_content["s3_error"] = s3_error

            return JSONResponse(
                status_code=200,
                content=response_content,
            )

        finally:
            # Clean up temporary file
            os.unlink(tmp_file_path)

    except Exception as e:
        logger.error(f"Error processing file {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@app.get("/query")
async def query_documents(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Number of results to return"),
):
    """Query documents using similarity search"""
    try:
        # query_engine = index.as_query_engine(
        #     similarity_top_k=limit,
        #     response_mode="no_text"
        # )

        # Get nodes instead of response
        retriever = index.as_retriever(similarity_top_k=limit)
        nodes = retriever.retrieve(q)

        results = []
        for node in nodes:
            results.append(
                {
                    "id": node.node_id,
                    "text": node.text,
                    "score": node.score,
                    "metadata": node.metadata,
                }
            )

        return {"query": q, "results": results, "total_results": len(results)}

    except Exception as e:
        logger.error(f"Error querying documents: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error querying documents: {str(e)}"
        )


@app.get("/chunks")
async def list_chunks(limit: int = Query(100, ge=1, le=1000)):
    """List all document chunks in the index"""
    try:
        # Get all vectors from Pinecone (this is a basic implementation)
        stats = pinecone_index.describe_index_stats()

        # For a more detailed listing, we'd need to implement pagination
        # This is a simplified version showing stats
        return {
            "total_vectors": stats.get("total_vector_count", 0),
            "index_fullness": stats.get("index_fullness", 0),
            "namespaces": stats.get("namespaces", {}),
            "note": "Use /query endpoint to search specific chunks",
        }

    except Exception as e:
        logger.error(f"Error listing chunks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing chunks: {str(e)}")


@app.get("/stats")
async def get_index_stats():
    """Get Pinecone index statistics"""
    try:
        stats = pinecone_index.describe_index_stats()

        # Convert to JSON-serializable format
        serializable_stats = {
            "total_vector_count": stats.get("total_vector_count", 0),
            "index_fullness": stats.get("index_fullness", 0.0),
            "dimension": stats.get("dimension", 0),
        }

        # Handle namespaces if present
        if hasattr(stats, "namespaces") and stats.namespaces:
            serializable_stats["namespaces"] = {}
            for ns, ns_stats in stats.namespaces.items():
                serializable_stats["namespaces"][ns] = {
                    "vector_count": (
                        ns_stats.get("vector_count", 0)
                        if hasattr(ns_stats, "get")
                        else getattr(ns_stats, "vector_count", 0)
                    )
                }

        return {"index_name": "caseforai-embeddings", "stats": serializable_stats}

    except Exception as e:
        logger.error(f"Error getting index stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
