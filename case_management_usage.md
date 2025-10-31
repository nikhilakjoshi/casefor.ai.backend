# Case Management Usage

## Overview
The `/upload` endpoint has been enhanced to support case-based document management. Each uploaded document must be associated with a `case_id` and can optionally include a `case_document_id` for more granular organization.

## Upload Endpoint

### Endpoint
```
POST /upload
```

### Parameters
- **file** (required): The document file to upload
  - Supported formats: `.pdf`, `.docx`, `.txt`, `.md`, `.xlsx`
- **case_id** (required): Unique identifier for the case
- **case_document_id** (optional): Specific document identifier within the case

### Example Usage

#### Basic Upload with Case ID
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@document.pdf" \
  -F "case_id=CASE-2024-001"
```

#### Upload with Case and Document IDs
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@contract.pdf" \
  -F "case_id=CASE-2024-001" \
  -F "case_document_id=DOC-CONTRACT-001"
```

### Response
```json
{
  "message": "File uploaded and processed successfully",
  "filename": "contract.pdf",
  "case_id": "CASE-2024-001",
  "case_document_id": "DOC-CONTRACT-001",
  "documents_processed": 1,
  "chunks_created": 15,
  "file_type": ".pdf",
  "s3_url": "https://bucket.s3.amazonaws.com/documents/2024/10/28/abc123_contract.pdf"
}
```

## Metadata Storage
Each document chunk stored in Pinecone includes:
- `filename`: Original filename
- `file_type`: File extension
- `upload_timestamp`: ISO timestamp
- `case_id`: Case identifier (mandatory)
- `case_document_id`: Document identifier (optional)

## Error Handling
- Missing `case_id` returns 422 validation error
- Unsupported file types return 400 error
- Processing failures return 500 error