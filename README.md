# OLX Buddy

Web app for managing Vinted/OLX sales: generate descriptions, track listings, monitor competitor prices, analyze sales.

## Features

- 🤖 AI-powered description generator
- 📊 Listing tracker (Vinted + OLX)
- 💰 Competitor price monitoring
- 📈 Sales analytics

## Tech Stack

- **Backend:** Python + FastAPI + SQLAlchemy
- **Frontend:** Vue.js 3
- **Database:** PostgreSQL
- **Scheduler:** APScheduler
- **Deploy:** Docker

## Setup

### Prerequisites

- [mise](https://mise.jdx.dev/)
- PostgreSQL database

### Development

```bash
# Install dependencies
mise install

# Backend
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Frontend
cd frontend
npm install

# Run migrations
cd backend
alembic upgrade head

# Start backend
uvicorn app.main:app --reload

# Start frontend
cd frontend
npm run dev
```

## Environment Variables

```env
DATABASE_URL=postgresql://user:pass@host:5432/olxbuddy
OPENAI_API_KEY=sk-...
SECRET_KEY=your-secret-key
```

## Docker

```bash
docker compose up
```

## License

MIT
