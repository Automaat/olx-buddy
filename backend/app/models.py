"""Database models."""

from datetime import datetime

from sqlalchemy import DECIMAL, JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Listing(Base):
    """Listing model for tracking items on Vinted/OLX."""

    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    external_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float | None] = mapped_column(DECIMAL(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="PLN")
    category: Mapped[str | None] = mapped_column(String(100))
    brand: Mapped[str | None] = mapped_column(String(100))
    condition: Mapped[str | None] = mapped_column(String(50))
    size: Mapped[str | None] = mapped_column(String(50))
    views: Mapped[int] = mapped_column(Integer, default=0)
    images: Mapped[dict | None] = mapped_column(JSON)
    platform_metadata: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="active")
    posted_at: Mapped[datetime | None] = mapped_column(DateTime)
    sold_at: Mapped[datetime | None] = mapped_column(DateTime)
    sale_price: Mapped[float | None] = mapped_column(DECIMAL(10, 2))
    initial_cost: Mapped[float | None] = mapped_column(DECIMAL(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    price_history: Mapped[list[PriceHistory]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )
    competitor_prices: Mapped[list[CompetitorPrice]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )


class PriceHistory(Base):
    """Price history for tracking listing price changes."""

    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    listing_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    listing: Mapped[Listing] = relationship(back_populates="price_history")


class CompetitorPrice(Base):
    """Competitor prices for market analysis."""

    __tablename__ = "competitor_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    listing_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str | None] = mapped_column(String(20))
    competitor_url: Mapped[str | None] = mapped_column(Text)
    competitor_title: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float | None] = mapped_column(DECIMAL(10, 2))
    similarity_score: Mapped[float | None] = mapped_column(DECIMAL(3, 2))
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    listing: Mapped[Listing] = relationship(back_populates="competitor_prices")


class Monitor(Base):
    """Search monitors for tracking specific queries."""

    __tablename__ = "monitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    platform: Mapped[str | None] = mapped_column(String(20))
    search_query: Mapped[str | None] = mapped_column(Text)
    filters: Mapped[dict | None] = mapped_column(JSON)
    notify_telegram: Mapped[bool] = mapped_column(Boolean, default=False)
    last_checked: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class JobExecution(Base):
    """Job execution history for scheduler monitoring."""

    __tablename__ = "job_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[str] = mapped_column(String(100), nullable=False)
    job_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(Text)
    result_data: Mapped[dict | None] = mapped_column(JSON)
