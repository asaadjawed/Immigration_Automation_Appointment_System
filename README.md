# Immigration Office Automation System

An automated email workflow system for processing immigration office requests using AI/LLM technology.

## Features

- 📧 **Automated Email Processing**: Fetches and processes immigration-related emails from IMAP
- 📄 **PDF Text Extraction**: Extracts text from PDF documents using pdfplumber and PyPDF2
- 🤖 **AI-Powered Analysis**: Uses Google Gemini LLM for request categorization and compliance checking
- 🔍 **RAG (Retrieval Augmented Generation)**: Compares student documents with official guidelines
- 📅 **Appointment Scheduling**: Automatically schedules appointments for compliant requests
- 📊 **Vector Database**: Stores and retrieves document embeddings using ChromaDB
- ⚡ **Async Processing**: Uses Celery for background task processing

## Tech Stack

- **Backend**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Vector DB**: ChromaDB
- **LLM**: Google Gemini (via LangChain)
- **Task Queue**: Celery with Redis
- **Email**: IMAP/SMTP
- **PDF Processing**: pdfplumber, PyPDF2

## Prerequisites

- Python 3.8+
- PostgreSQL
- Redis
- Google Gemini API Key

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd OptimigrationCaseStudy
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Set up the database:
```bash
# Run migrations
alembic upgrade head
```

6. Load guidelines:
```bash
python load_guidelines.py
```

## Running the Application

1. Start Redis (required for Celery):
```bash
redis-server
```

2. Start Celery worker:
```bash
celery -A app.celery_app worker --loglevel=info
```

3. Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

## Project Structure

```
OptimigrationCaseStudy/
├── app/
│   ├── api/           # API routes
│   ├── services/       # Business logic services
│   ├── workers/       # Celery tasks
│   ├── models.py      # Database models
│   ├── database.py    # Database configuration
│   ├── config.py      # Application settings
│   └── main.py        # FastAPI application
├── alembic/           # Database migrations
├── guidelines/        # Immigration guidelines (text files)
├── uploads/           # Uploaded documents
├── vector_db/         # ChromaDB vector database
└── requirements.txt  # Python dependencies
```

## Key Features

### Email Processing
- Automatically fetches emails from today only
- Filters for immigration-related keywords
- Extracts PDF attachments
- Processes documents asynchronously

### PDF Text Extraction
- Primary: pdfplumber
- Fallback: PyPDF2
- Extracts metadata (pages, title, author)

### AI Analysis
- Categorizes requests using LLM
- Checks document compliance with guidelines
- Generates compliance reports

### Appointment Scheduling
- Automatically schedules appointments for compliant requests
- Sends confirmation emails

