# Vinted/OLX Sales Helper Webapp - Implementation Plan

## Overview
Web app to help manage Vinted/OLX sales: generate descriptions, track listings, monitor competitor prices, analyze sales. Manual posting to platforms (no automated posting risk).

## Architecture

### Simplified Stack
- **Single Docker container:** Python FastAPI webapp
- **Database:** Existing PostgreSQL (home-assistant instance)
- **Scheduler:** APScheduler (in-process, no Redis/Celery)
- **Frontend:** Vue.js or React SPA
- **Deploy:** Docker + Traefik/Nginx on homelab

### No Extra Dependencies
- No Celery worker
- No Redis
- No separate postgres container

## Core Features

### 1. AI Description Generator
**Purpose:** Create compelling listing descriptions from photos/details

**Flow:**
1. Upload item photos
2. Enter: category, brand, condition, size
3. AI generates description (engaging, keyword-rich)
4. Suggests price based on similar items
5. Copy/paste to Vinted/OLX manually

**Tech:**
- Image analysis: OpenAI Vision API / Claude API / Local LLM (Ollama)
- Price suggestion: scrape similar items, calculate median/percentiles
- Template system for different categories

### 2. Listing Tracker
**Purpose:** Centralized view of all active listings

**Flow:**
1. After posting on platform, paste URL into app
2. App scrapes details: title, price, views, photos, status
3. Stores in PostgreSQL
4. Dashboard displays all listings (sortable, filterable)
5. APScheduler job auto-refreshes data (every 30min)

**Data Tracked:**
- Platform (Vinted/OLX)
- External ID
- Title, description
- Current price
- Views count (if available)
- Posted date
- Last updated
- Status (active/sold/removed)

### 3. Competitor Price Monitoring
**Purpose:** Know if you're priced competitively

**Flow:**
1. For each listing, app searches similar items on both platforms
2. Background job (APScheduler) scrapes competitor prices daily
3. Stores price history
4. Dashboard shows: your price vs market (median, min, max)
5. Alerts if significantly overpriced/underpriced

**Implementation:**
- Use `kjanus03/olx-scrapper` for OLX.pl
- Use `vinted-api-kit` or similar for Vinted
- Simple matching: same category + brand + condition
- Rate limiting: 1 req/5sec to avoid blocks

### 4. Sales Analytics
**Purpose:** Understand what sells best

**Features:**
- Mark items as sold (manual button)
- Enter actual sale price (may differ from listing)
- Calculate profit (sale price - initial cost)
- Graphs: sales over time, revenue, avg sell time
- Best-selling categories/brands
- Inventory value (active listings total)

## Database Schema

```sql
-- Main listings table
CREATE TABLE listings (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,  -- 'vinted' or 'olx'
    external_id VARCHAR(100) UNIQUE NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    description TEXT,
    price DECIMAL(10,2),
    currency VARCHAR(3) DEFAULT 'PLN',
    category VARCHAR(100),
    brand VARCHAR(100),
    condition VARCHAR(50),
    size VARCHAR(50),
    views INTEGER DEFAULT 0,
    images JSONB,  -- array of image URLs
    metadata JSONB,  -- platform-specific data
    status VARCHAR(20) DEFAULT 'active',  -- active, sold, removed
    posted_at TIMESTAMP,
    sold_at TIMESTAMP,
    sale_price DECIMAL(10,2),
    initial_cost DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Price history for tracking changes
CREATE TABLE price_history (
    id SERIAL PRIMARY KEY,
    listing_id INTEGER REFERENCES listings(id) ON DELETE CASCADE,
    price DECIMAL(10,2) NOT NULL,
    recorded_at TIMESTAMP DEFAULT NOW()
);

-- Competitor prices for market analysis
CREATE TABLE competitor_prices (
    id SERIAL PRIMARY KEY,
    listing_id INTEGER REFERENCES listings(id) ON DELETE CASCADE,
    platform VARCHAR(20),
    competitor_url TEXT,
    competitor_title TEXT,
    price DECIMAL(10,2),
    similarity_score FLOAT,  -- how similar to our item
    scraped_at TIMESTAMP DEFAULT NOW()
);

-- Search monitors (optional feature)
CREATE TABLE monitors (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(20),
    search_query TEXT,
    filters JSONB,
    notify_telegram BOOLEAN DEFAULT false,
    last_checked TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_listings_platform ON listings(platform);
CREATE INDEX idx_listings_status ON listings(status);
CREATE INDEX idx_price_history_listing ON price_history(listing_id);
CREATE INDEX idx_competitor_prices_listing ON competitor_prices(listing_id);
```

## Tech Stack Details

### Backend (Python)
- **Framework:** FastAPI
- **ORM:** SQLAlchemy 2.0
- **Migrations:** Alembic
- **Scheduler:** APScheduler (BackgroundScheduler)
- **HTTP Client:** httpx (async)
- **Scraping:**
  - OLX: Fork/adapt `kjanus03/olx-scrapper`
  - Vinted: `vinted-api-kit` or custom wrapper
- **AI:** OpenAI SDK / Anthropic SDK / Ollama Python client
- **Image Processing:** Pillow (resize/optimize before upload)

### Frontend
- **Framework:** Vue.js 3 (Composition API) OR React
- **UI:** Tailwind CSS + shadcn/ui or similar
- **Charts:** Chart.js or Recharts
- **State:** Pinia (Vue) / Zustand (React)
- **HTTP:** axios or fetch

### DevOps
- **Dependency Mgmt:** mise (Python, Node.js versions)
- **Docker:** Multi-stage build (smaller image)
- **Reverse Proxy:** Traefik or Nginx
- **Secrets:** Environment variables via Docker Compose

## Implementation Steps

### Phase 1: Project Setup
1. Initialize FastAPI project structure
2. Setup mise config (Python 3.11+, Node.js 20+)
3. Configure SQLAlchemy + Alembic
4. Create database schema (run migrations against homelab postgres)
5. Docker Compose file (webapp + connection to existing postgres)
6. Basic FastAPI endpoints (health check, CRUD for listings)

### Phase 2: Scraping Integration
7. Integrate OLX scraping (adapt `kjanus03/olx-scrapper`)
8. Integrate Vinted scraping (`vinted-api-kit` or custom)
9. Implement "Add Listing by URL" endpoint
10. Rate limiting + session management
11. Error handling for scraping failures

### Phase 3: AI Description Generator
12. Setup AI client (OpenAI/Anthropic/Ollama)
13. Create prompt templates for different categories
14. Image upload endpoint (save locally or S3-compatible)
15. Generate description endpoint (multimodal: images + text)
16. Price suggestion logic (scrape similar + calculate)

### Phase 4: Scheduler & Monitoring
17. Setup APScheduler in FastAPI
18. Job: Refresh listing data (views, status) - every 30min
19. Job: Scrape competitor prices - daily
20. Job: Cleanup old data - weekly
21. Store results in database

### Phase 5: Analytics
22. Sales tracking endpoints (mark as sold, enter profit)
23. Analytics queries (SQLAlchemy aggregations)
24. Dashboard data endpoints (revenue, best sellers, etc.)

### Phase 6: Frontend
25. Setup Vue.js/React project
26. Dashboard: listing cards with price/views/status
27. Add Listing form (URL input)
28. Description Generator form (photo upload + fields)
29. Analytics page (charts, stats)
30. Responsive design

### Phase 7: Deployment
31. Multi-stage Dockerfile (build frontend, copy to static)
32. Docker Compose with env vars for postgres connection
33. Traefik/Nginx config for homelab
34. SSL/TLS setup (Let's Encrypt or self-signed)
35. Health monitoring

## APScheduler Jobs

```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

# Refresh all active listings (check views, status changes)
scheduler.add_job(
    func=refresh_active_listings,
    trigger="interval",
    minutes=30,
    id="refresh_listings"
)

# Scrape competitor prices for market analysis
scheduler.add_job(
    func=scrape_competitor_prices,
    trigger="cron",
    hour=3,  # 3 AM daily
    id="competitor_prices"
)

# Cleanup old data (competitor prices >30 days)
scheduler.add_job(
    func=cleanup_old_data,
    trigger="cron",
    day_of_week="sun",
    hour=4,
    id="cleanup"
)

scheduler.start()
```

## API Endpoints (Draft)

### Listings
- `POST /api/listings/add-by-url` - Add listing by pasting URL
- `GET /api/listings` - List all listings (with filters)
- `GET /api/listings/{id}` - Get listing details
- `PATCH /api/listings/{id}` - Update listing (manual edits)
- `POST /api/listings/{id}/mark-sold` - Mark as sold
- `DELETE /api/listings/{id}` - Remove from tracking

### Description Generator
- `POST /api/generate/upload-images` - Upload photos
- `POST /api/generate/description` - Generate description + price
- `GET /api/generate/categories` - List supported categories

### Analytics
- `GET /api/analytics/summary` - Overall stats (revenue, count, etc.)
- `GET /api/analytics/sales-over-time` - Time series data
- `GET /api/analytics/best-sellers` - Top categories/brands
- `GET /api/analytics/inventory-value` - Total value of active listings

### Price Monitoring
- `GET /api/price-monitoring/{listing_id}` - Competitor prices for item
- `GET /api/price-monitoring/{listing_id}/history` - Price history graph data

## Docker Setup

### Dockerfile
```dockerfile
FROM python:3.11-slim AS backend-build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY --from=backend-build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .
COPY --from=frontend-build /app/dist /app/static
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  olx-buddy:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@homelab-postgres:5432/olxbuddy
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./uploads:/app/uploads
    restart: unless-stopped
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.olx-buddy.rule=Host(`olx-buddy.homelab.local`)"
```

## Configuration (Environment Variables)

```env
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# AI Service (choose one)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_BASE_URL=http://ollama:11434

# Security
SECRET_KEY=random-secret-for-sessions

# Scraping
SCRAPE_RATE_LIMIT=5  # seconds between requests
USE_PROXIES=false

# Optional
TELEGRAM_BOT_TOKEN=...  # for notifications
```

## Risk Mitigation

### Scraping Best Practices
1. **Rate limiting:** Minimum 5 sec between requests
2. **Session rotation:** Refresh cookies periodically
3. **User-Agent rotation:** Mimic real browsers
4. **Error handling:** Graceful degradation if scraper blocked
5. **Manual fallback:** Always allow manual data entry

### Vinted-Specific Risks
- **Datadome protection:** May block aggressive scraping
- **Solution:** Conservative rate limits, read-only operations
- **Fallback:** Manual URL entry without auto-refresh

### OLX
- Lower risk (can potentially use official API later)
- Scraping for read-only acceptable with rate limits

## Future Enhancements (Optional)

### Phase 8+
- **Telegram bot:** Notifications for sales, price alerts
- **Bulk import:** CSV upload of existing listings
- **Templates:** Save description templates for common items
- **Photo optimization:** Auto-resize/compress before description gen
- **Multi-user:** Auth system for household members
- **Export:** Sales data to CSV/Excel for accounting
- **Integrations:** Sync with accounting software
- **Mobile:** PWA support for mobile usage
- **Auto-relist:** Suggestion to relist stale items

## Open Questions

1. **AI Model Choice:**
   - OpenAI GPT-4V: Best quality, costs per API call
   - Claude 3: Good vision, Anthropic API
   - Ollama (Llama 3.2 Vision): Free, runs locally, needs GPU

2. **Frontend Framework:**
   - Vue.js: Simpler, less boilerplate
   - React: More ecosystem, familiar to many

3. **PostgreSQL Connection:**
   - Same DB as home-assistant or separate schema/database?
   - Connection pooling settings?

4. **Homelab Constraints:**
   - Available RAM/CPU for image processing?
   - Storage for uploaded photos?
   - Existing reverse proxy setup?

## Success Metrics

- **Time saved:** Reduce listing creation from 15min to 5min
- **Better pricing:** Avg 10-15% higher sale prices via competitor data
- **Visibility:** Track views/engagement in one place
- **Insights:** Understand what sells best to optimize inventory

## Timeline Estimate (Solo Dev)

- **Phase 1-2:** 1 week (backend + scraping)
- **Phase 3-4:** 1 week (AI + scheduler)
- **Phase 5-6:** 1-2 weeks (analytics + frontend)
- **Phase 7:** 2-3 days (deployment + testing)

**Total:** 3-4 weeks part-time (evenings/weekends)
