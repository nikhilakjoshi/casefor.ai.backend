# Document Retrieval Usage

## Overview
The `/documents` endpoint retrieves and concatenates all documents associated with a specific case ID or case document ID. The response includes both structured data and markdown-formatted content.

## Documents Endpoint

### Endpoint
```
GET /documents
```

### Parameters
- **case_id** (required): Case identifier to filter documents
- **case_document_id** (optional): Specific document identifier for more granular filtering

### Example Usage

#### Retrieve All Documents for a Case
```bash
curl "http://localhost:8000/documents?case_id=CASE-2024-001"
```

#### Retrieve Specific Document
```bash
curl "http://localhost:8000/documents?case_id=CASE-2024-001&case_document_id=DOC-CONTRACT-001"
```

### Response Structure
```json
{
  "case_id": "CASE-2024-001",
  "case_document_id": "DOC-CONTRACT-001",
  "total_documents": 2,
  "documents": [
    {
      "filename": "contract.pdf",
      "content": "Full concatenated content of all chunks...",
      "case_id": "CASE-2024-001",
      "case_document_id": "DOC-CONTRACT-001",
      "chunk_count": 15,
      "upload_timestamp": "2024-10-28T10:30:00"
    }
  ],
  "markdown_content": "# contract.pdf\n\nFull document content...\n\n---\n\n# other-doc.pdf\n\nOther content..."
}
```

## Response Fields

### DocumentsResponse
- **case_id**: The requested case ID
- **case_document_id**: The requested document ID (if provided)
- **total_documents**: Number of documents found
- **documents**: Array of DocumentResponse objects
- **markdown_content**: All documents formatted as markdown

### DocumentResponse
- **filename**: Original filename
- **content**: Concatenated text content from all chunks
- **case_id**: Case identifier
- **case_document_id**: Document identifier (may be null)
- **chunk_count**: Number of chunks that were concatenated
- **upload_timestamp**: When the document was uploaded

## Markdown Format
The `markdown_content` field contains all documents formatted as:
```markdown
# filename1.pdf

Full content of document 1...

---

# filename2.docx

Full content of document 2...
```

## Error Handling
- Missing `case_id` returns 422 validation error
- No documents found returns empty arrays but 200 status
- Processing failures return 500 error

## Notes
- Documents are concatenated from chunks in order
- All chunks for a case/document are retrieved (no pagination)
- Text content is extracted from Pinecone metadata
- Documents are sorted by filename for consistent output