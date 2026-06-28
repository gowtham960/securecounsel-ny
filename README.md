# securecounsel-ny
# SecureCounsel NY

SecureCounsel NY is a full-stack legal AI workspace for matter-based document intelligence. It demonstrates secure document upload, role-based access control, matter-scoped retrieval, evidence grading, grounded answer generation, citations, and audit-ready metadata.

## What It Does

- Lets demo users access only their assigned matters.
- Lets users upload matter-specific documents.
- Extracts searchable text from uploaded files.
- Searches only authorized matter sources.
- Selects relevant evidence before answering.
- Generates grounded answers with citations.
- Shows security, evidence, and retrieval metadata.

## Supported Upload Types

- TXT
- PDF
- DOCX
- XLSX
- CSV

## Demo Users

- Ava Johnson — Attorney
- Ben Carter — Paralegal
- Maria Lopez — Firm Admin

## Core Features

- Demo login and RBAC
- Assigned matter cards
- Matter workspace
- Matter chat
- Search scope selector
- Multi-file document upload
- Uploaded document list
- Local hybrid retrieval MVP
- Evidence grading
- Evidence selection
- Citation filtering
- CSV/table-aware answer generation
- Prompt-injection check
- PII redaction check
- Audit-ready response metadata

## Tech Stack

### Backend

- Python
- FastAPI
- Local document indexing
- Local hybrid retrieval MVP
- Groq-ready answer generation

### Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS

## Run Backend

```powershell
cd C:\Users\Gowtham\securecounsel-ny\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
Backend:

http://localhost:8000

Swagger:

http://localhost:8000/docs
Run Frontend
cd C:\Users\Gowtham\securecounsel-ny\frontend
npm run dev

Frontend:

http://localhost:3000
Example Demo Flow
Open the frontend.
Select Maria Lopez / Firm Admin.
Open the ACME matter.
Upload a CSV, PDF, DOCX, XLSX, or TXT file.
Ask a matter question.

Example:

When are invoices due?

Expected behavior:

The agent finds the relevant uploaded payment schedule.
It extracts invoice due dates and payment terms.
It gives a clean answer.
It cites the uploaded document chunks.
Current Status:

This project currently has a working MVP for secure matter-based document Q&A with uploaded document retrieval, evidence selection, citations, and table-aware answers.

Known Limitations:
Retrieval is still local MVP, not production vector search.
Dense search is placeholder/local.
Uploaded document registry is in-memory.
Scanned PDFs do not have OCR yet.
Supabase persistence is not added yet.
Qdrant vector database is not added yet.
Production reranker is not added yet.
Next Steps:
Add document selection trace to debug and audit logs.
Rebuild uploaded document registry from disk after restart.
Add Supabase persistence.
Add Qdrant vector search.
Add real embeddings.
Add production reranking.
Add OCR for scanned PDFs.
Add legal drafting workflows.