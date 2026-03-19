# TradeStamp Backend

A Python FastAPI backend for the TradeStamp application.

## Getting Started

### Prerequisites

- Python 3.10+

### Setup

1. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the development server:

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

### API Docs

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
