# OLX Buddy

Web app for managing Vinted/OLX sales: AI-powered description generation, listing tracking, competitor price monitoring, sales analytics.

**Tech Stack:** Python 3.14 + FastAPI + SQLAlchemy 2.0, Vue.js 3 + TypeScript, PostgreSQL 18, APScheduler

**Purpose:** Automate Vinted/OLX seller workflows—generate compelling product descriptions using AI vision models, track listings across platforms, monitor competitor pricing, analyze sales performance.

---

## Project Structure

### Directory Layout

```
backend/
├── app/
│   ├── routers/       # API endpoints (listings, generate, scheduler, analytics)
│   ├── services/      # Business logic (ai, scraper, analytics, storage)
│   ├── models.py      # SQLAlchemy 2.0 models
│   ├── schemas.py     # Pydantic request/response schemas
│   ├── crud.py        # Database operations
│   ├── database.py    # DB session management
│   ├── config.py      # Settings (pydantic-settings)
│   ├── scheduler.py   # APScheduler job definitions
│   └── main.py        # FastAPI app
├── alembic/           # Database migrations
└── tests/             # Mirrors app/ structure

frontend/
├── src/
│   ├── views/         # Vue pages (Dashboard, AddListing, DescriptionGenerator)
│   ├── components/    # Reusable Vue components
│   ├── services/      # API client (axios)
│   ├── types/         # TypeScript interfaces
│   ├── router/        # Vue Router
│   └── main.ts        # App entry point
└── tests/

.mise.toml             # Tool versions + dev tasks
docker-compose.yml     # Production stack
docker-compose.dev.yml # Dev stack (includes Ollama)
```

### Key Modules

- **Routers** (`backend/app/routers/`) - FastAPI endpoints, request validation, HTTPException handling
- **Services** (`backend/app/services/`) - Core business logic: AI fallback chain, web scraping, analytics, image storage
- **CRUD** (`backend/app/crud.py`) - Database operations, SQLAlchemy queries
- **Models** (`backend/app/models.py`) - SQLAlchemy 2.0 declarative models with `Mapped[]` types
- **Scheduler** (`backend/app/scheduler.py`) - Background jobs for price monitoring, listing refresh

---

## Development Workflow

### Before Coding

1. **ASK clarifying questions** until 95% confident about requirements
2. **Research existing patterns** - search codebase for similar implementations
3. **Create plan** and get approval before implementing
4. **Work incrementally** - one focused task at a time

### Recommended Workflow

**Explore → Plan → Code → Test → Commit**

- Use **Plan Mode** (Shift+Tab twice) for complex tasks
- Search codebase for similar patterns before proposing new approaches
- Propose plan with alternatives when multiple approaches exist
- **Do NOT code until plan is confirmed**
- All new code must have tests before committing

---

## Python Conventions

### Code Style

- **Formatter:** ruff format (100 line length)
- **Linter:** ruff (pycodestyle, pyflakes, isort, flake8-bugbear, comprehensions, pyupgrade)
- **Type Checker:** pyrefly (Python 3.14)
- **Naming:** snake_case for functions/variables, PascalCase for classes
- **Line length:** 100 characters max
- **Python version:** 3.14+, use modern syntax

### Modern Python Patterns

**Union Types (3.10+ syntax):**
```python
# Use | instead of Union[]
def get_listing(db: Session, listing_id: int) -> Listing | None:
    """Get listing by ID."""
    return db.query(Listing).filter(Listing.id == listing_id).first()
```

**SQLAlchemy 2.0 with Mapped[]:**
```python
from sqlalchemy.orm import Mapped, mapped_column

class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[float | None] = mapped_column(DECIMAL(10, 2))
    images: Mapped[dict | None] = mapped_column(JSON)

    # Relationships with cascade
    price_history: Mapped[list[PriceHistory]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )
```

**Import Organization:**
```python
# Group by type: stdlib → third-party → local
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.config import settings
from app.database import get_db
```

### Linter Errors

**ALWAYS:**
- Attempt to fix linter errors properly
- Research solutions online if unclear how to fix
- Fix root cause, not symptoms

**NEVER:**
- Use skip/disable directives (`# noqa`, `# ruff: noqa`, `# type: ignore`)
- Ignore linter warnings
- Work around linter errors

**If stuck:**
- Try fixing the error
- Research online for proper solution
- If still unclear after research, ASK what to do (don't skip/disable)

### Error Handling

**Pattern 1: Services log and propagate**
```python
# In services/ai.py - fallback chain
if self.openai_client:
    try:
        return await self._generate_with_openai(prompt, image_paths)
    except Exception as e:
        logger.warning("OpenAI generation failed: %s", e)

if self.anthropic_api_key:
    try:
        return await self._generate_with_anthropic(prompt, image_paths)
    except Exception as e:
        logger.warning("Anthropic generation failed: %s", e)

# All providers failed
msg = "No AI provider available or all providers failed"
raise RuntimeError(msg)
```

**Pattern 2: Routers raise HTTPException**
```python
# In routers/listings.py
listing = crud.get_listing(db, listing_id)
if not listing:
    raise HTTPException(status_code=404, detail="Listing not found")
return listing
```

**Pattern 3: Job execution tracking**
```python
# In scheduler.py
db = SessionLocal()
execution = None

try:
    execution = create_job_execution(db, "refresh_listings", "Refresh active listings")
    logger.info("Starting job (execution_id=%d)", execution.id)

    # ... do work ...

    result = {"updated": updated_count, "errors": error_count}
    update_job_execution(db, execution.id, "success", result_data=result)
except Exception as e:
    logger.exception("refresh_active_listings job failed")
    if execution:
        update_job_execution(db, execution.id, "error", error_message=str(e))
finally:
    db.close()
```

**Logging Policy:**
- Log ALL exceptions (use `logger.exception()` in except blocks)
- Use `%s` formatting, not f-strings in log messages
- Levels: DEBUG for trace, INFO for milestones, WARNING for recoverable errors, ERROR/EXCEPTION for failures

### Async/Await Patterns

**Preferred: Async for I/O operations**
```python
# Service methods are async
class AIService:
    async def generate_description(
        self,
        category: str,
        image_paths: list[str],
        brand: str | None = None,
    ) -> str:
        prompt = self._build_prompt(category, brand, condition, size, additional_details)
        return await self._generate_with_openai(prompt, image_paths)

# HTTP clients use async context managers
async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
    response = await client.get(search_url, follow_redirects=True)
    response.raise_for_status()
    return response.json()

# Parallel operations with gather
olx_task = self._search_olx(search_query, category, max_results // 2)
vinted_task = self._search_vinted(search_query, category, brand, max_results // 2)
olx_items, vinted_items = await asyncio.gather(olx_task, vinted_task, return_exceptions=True)
```

**Scheduler jobs: sync wrapper around async logic**
```python
# Job functions are sync (APScheduler requirement)
def refresh_competitor_prices():
    """Scheduled job to refresh competitor prices."""
    async def process_listings():
        # async work here
        return total_competitors, error_count

    # Bridge to async
    total_competitors, error_count = asyncio.run(process_listings())
```

### Type Hints

**Required for all function signatures:**
```python
# Complete type annotations
def create_price_history(
    db: Session, listing_id: int, price: float, source: str = "manual"
) -> PriceHistory:
    """Create price history entry."""

# Async functions
async def suggest_price(
    self,
    search_query: str,
    category: str | None = None,
) -> dict[str, Any]:
    """Suggest price based on similar items."""

# Use cast() for runtime type assertions
from typing import cast
update_job_execution(db, cast(int, execution.id), "success")
```

### Documentation

**Docstrings required for all public functions/methods:**
```python
def suggest_price(
    self,
    search_query: str,
    category: str | None = None,
    brand: str | None = None,
    condition: str | None = None,
) -> dict[str, Any]:
    """Suggest price based on similar items.

    Args:
        search_query: Text to search for similar items
        category: Optional category filter
        brand: Optional brand filter
        condition: Item condition - new, like_new, good, fair, poor

    Returns:
        Dict containing suggested_price, min/max/median prices, sample_size,
        and list of similar_items with similarity scores.
    """
```

**Pydantic schemas use Field descriptions:**
```python
class ListingCreate(BaseModel):
    platform: str = Field(..., description="Platform name: vinted or olx")
    external_id: str = Field(..., description="External platform ID")
```

### Testing

- **Framework:** pytest + pytest-asyncio + pytest-cov
- **Coverage:** Required for all new code, target 80%+
- **Structure:** Mirror source (`tests/test_*.py` matches `app/*.py`)
- **Policy:** ALL new code must have tests before committing

**Test Pattern:**
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

class TestPriceHistoryCRUD:
    """Test PriceHistory CRUD operations."""

    def test_create_price_history(self, mock_db):
        """Test creating price history entry."""
        result = create_price_history(mock_db, 1, 50.0, "manual")

        assert mock_db.add.called
        assert result.listing_id == 1
        assert result.price == 50.0

@pytest.fixture
def mock_db():
    """Create mock database session."""
    return MagicMock()

# Async tests
@pytest.mark.asyncio
async def test_generate_with_anthropic(ai_service_with_anthropic, test_image_path):
    """Test Anthropic description generation."""
    with (
        patch("httpx.AsyncClient") as mock_client,
        patch.object(ai_service_with_anthropic, "_load_image_base64", return_value="base64data"),
    ):
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": [{"text": "Generated description"}]}
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        result = await ai_service_with_anthropic._generate_with_anthropic("prompt", [test_image_path])

        assert result == "Generated description"
```

---

## Database & Migrations

### ORM Patterns

**SQLAlchemy 2.0 declarative style:**
```python
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Listing(Base):
    __tablename__ = "listings"

    # Use Mapped[] for all columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[float | None] = mapped_column(DECIMAL(10, 2))

    # Relationships with type hints
    price_history: Mapped[list[PriceHistory]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )
```

**Query patterns:**
```python
# Method chaining with filters
query = db.query(Listing)
if platform:
    query = query.filter(Listing.platform == platform)
if status:
    query = query.filter(Listing.status == status)
return query.offset(skip).limit(limit).all()

# Aggregations
result = db.query(
    func.sum(Listing.sale_price).label("total_revenue"),
    func.avg(Listing.sale_price).label("avg_sale_price"),
    func.count(Listing.id).label("total_sales"),
).filter(Listing.status == "sold").first()
```

### Migrations

**Always use autogenerate, then review:**
```bash
cd backend
uv run alembic revision --autogenerate -m "Add job_execution table"
# Review generated file in alembic/versions/
# Edit if needed (indexes, constraints, data migrations)
uv run alembic upgrade head
```

**Migration structure:**
```python
def upgrade() -> None:
    op.create_table(
        "listings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index(op.f("ix_listings_id"), "listings", ["id"], unique=False)

def downgrade() -> None:
    op.drop_index(op.f("ix_listings_id"), table_name="listings")
    op.drop_table("listings")
```

---

## Frontend Conventions

### Vue.js 3 Patterns

**Composition API with `<script setup lang="ts">`:**
```typescript
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { Listing } from '@/types'
import api from '@/services/api'

const listings = ref<Listing[]>([])
const loading = ref(false)

const fetchListings = async () => {
  loading.value = true
  try {
    const response = await api.get('/api/listings')
    listings.value = response.data
  } catch (error) {
    console.error('Failed to fetch listings:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchListings()
})
</script>
```

**TypeScript strict mode:**
- All components use `lang="ts"`
- Props typed with interfaces
- API responses typed

**State Management:**
- Pinia stores for shared state
- Component-local state with `ref()`/`reactive()`

---

## Simplicity Principles

### Anti-Patterns to AVOID

❌ **NEVER:**
- Add abstractions for single-use code
- Create helper functions for one-off operations
- Design for hypothetical future requirements
- Add unnecessary error handling for scenarios that can't occur
- Over-validate internal function calls (trust type system)
- Use feature flags or backwards-compatibility shims when you can just change code
- Add comments explaining what code does (code should be self-documenting)
- Create base classes or protocols prematurely

### Enforcement Rules

✅ **ALWAYS:**
- Choose simplest solution that works
- Three similar lines > premature abstraction
- Only introduce complexity if clearly justified NOW
- Make minimal, surgical changes
- Search codebase for existing patterns FIRST
- Reuse existing CRUD/service methods
- Consistency > perfection

### Complexity Check

**Before implementing, ask:**
1. Can this be simpler?
2. Am I adding abstractions needed NOW (not future)?
3. Does similar code exist I can reuse?
4. Is this the minimal change to achieve the goal?

**If unsure:** STOP and ask for approval before proceeding.

---

## Code Generation Rules

### ALWAYS

- Show **complete code** (no placeholders, no `# ... rest of code ...`)
- **Incremental changes** - small focused steps (20-50 lines per change)
- **Surgical, minimal** modifications only
- **Follow existing patterns** found in codebase
- **Test before committing** - all new code needs tests
- **Ask questions** before assuming requirements

### NEVER

- Generate entire files at once
- Generate >100 lines in single response
- Make big changes in single step
- Modify code unrelated to the task
- Assume requirements without asking
- Add features beyond what's requested
- Use placeholders like `# TODO`, `# ... rest ...`

### Incremental Development

**Break changes into steps:**
1. Define types/schemas (Pydantic models)
2. Add database model if needed (+ migration)
3. Implement CRUD operations
4. Add service layer logic
5. Create router endpoints
6. Write tests for each layer
7. Iterate

**Each step:** Review, test, then proceed to next.

---

## Common Commands

### Setup

```bash
# Install tool versions
mise install

# Backend setup
cd backend
uv sync --all-extras

# Frontend setup
cd frontend
npm install

# Database migrations
cd backend
uv run alembic upgrade head
```

### Development

```bash
# Full dev stack (Docker: backend + frontend + PostgreSQL + Ollama)
mise run dev
mise run dev:logs
mise run dev:down

# Backend only
cd backend
uv run uvicorn app.main:app --reload

# Frontend only
cd frontend
npm run dev
```

### Testing

```bash
# Backend tests with coverage
cd backend
uv run pytest tests/ -v --cov=app --cov-report=xml

# Frontend tests
cd frontend
npm run test              # Run tests
npm run test:ui           # Run with UI
npm run test:coverage     # With coverage
```

### Linting & Formatting

```bash
# Backend
cd backend
uv run ruff check .           # Lint
uv run ruff format .          # Format
uv run pyrefly check .        # Type check

# Frontend
cd frontend
npm run lint                  # Lint (oxlint)
npm run type-check            # TypeScript check
```

### Database

```bash
cd backend
uv run alembic upgrade head                                    # Run migrations
uv run alembic revision --autogenerate -m "description"        # Create migration
uv run alembic downgrade -1                                     # Rollback one
uv run alembic current                                          # Show current revision
```

### Git Conventions

- **Commit signing:** Always use `-s -S` flags
- **Message format:** `"Phase N: Feature (#PR)"` or `"Update dependency X to vY (#PR)"`
- **CI requirement:** All checks must pass (backend + frontend lint, typecheck, test, coverage)

**Example commits:**
```bash
git commit -s -S -m "$(cat <<'EOF'
Phase 7: Add competitor price alerts

- Implemented email notifications for price changes
- Added threshold configuration per listing
- Created alert history tracking table

Closes #53
EOF
)"
```

---

## Domain Context

### Platform Knowledge

**OLX:**
- Polish classifieds marketplace (wider categories)
- URL pattern: `olx.pl/d/oferta/*-ID*.html`
- Scraping: BeautifulSoup, rate-limited (SCRAPE_RATE_LIMIT env var)

**Vinted:**
- Fashion-focused marketplace
- URL pattern: `vinted.pl/items/*-ID*`
- Scraping: JSON data in page HTML, requires headers to mimic browser

### AI Provider Fallback

**Chain:** OpenAI → Anthropic → Ollama (local dev)

- **OpenAI:** gpt-4o-mini with vision (primary, production)
- **Anthropic:** claude-3-5-sonnet with vision (fallback)
- **Ollama:** llama3.2-vision (local dev, no API key needed)

Each provider uses multi-modal prompts (text + images) for description generation.

### Price Suggestion Algorithm

1. Scrape similar items from both platforms (parallel)
2. Calculate text similarity using TF-IDF + cosine distance
3. Filter by similarity threshold (>0.1)
4. Return median/min/max prices + sample items

### Scheduler Jobs

- **refresh_competitor_prices:** Scrapes competitor listings for tracked items
- **refresh_active_listings:** Updates status/views for user's listings (placeholder, needs platform API)

---

## Environment Variables

```env
# Required
DATABASE_URL=postgresql://user:pass@localhost:5432/olxbuddy
SECRET_KEY=your-secret-key-for-jwt
OPENAI_API_KEY=sk-...

# Optional
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_BASE_URL=http://localhost:11434
SCRAPE_RATE_LIMIT=5                   # Requests per second
USE_PROXIES=false
SCHEDULER_JOB_LISTING_LIMIT=1000
TELEGRAM_BOT_TOKEN=                   # Future feature
```

---

## Notes

**Update this file when:**
- Adding new architecture patterns
- Changing code conventions
- Introducing new services/integrations
- Discovering common AI mistakes

**Keep under 500 lines:** Delete outdated sections as project evolves.
