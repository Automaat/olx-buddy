"""Analytics service for sales and inventory insights."""

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Listing


def get_analytics_summary(db: Session) -> dict:
    """Get overall analytics summary."""
    # Total listings by status
    active_count = db.query(Listing).filter(Listing.status == "active").count()
    sold_count = db.query(Listing).filter(Listing.status == "sold").count()

    # Revenue and profit (only sold items)
    sold_items = (
        db.query(
            func.sum(Listing.sale_price).label("total_revenue"),
            func.avg(Listing.sale_price).label("avg_sale_price"),
        )
        .filter(Listing.status == "sold", Listing.sale_price.isnot(None))
        .first()
    )

    # Calculate total profit
    profit_query = (
        db.query(func.sum(Listing.sale_price - Listing.initial_cost).label("total_profit"))
        .filter(
            Listing.status == "sold",
            Listing.sale_price.isnot(None),
            Listing.initial_cost.isnot(None),
        )
        .first()
    )

    # Inventory value (active listings with price)
    inventory_value = (
        db.query(func.sum(Listing.price).label("total_value"))
        .filter(Listing.status == "active", Listing.price.isnot(None))
        .first()
    )

    return {
        "total_listings": active_count + sold_count,
        "active_listings": active_count,
        "sold_listings": sold_count,
        "total_revenue": float(sold_items.total_revenue or 0),
        "avg_sale_price": float(sold_items.avg_sale_price or 0),
        "total_profit": float(profit_query.total_profit or 0),
        "inventory_value": float(inventory_value.total_value or 0),
    }


def get_sales_over_time(db: Session, period: str = "daily", days: int = 30) -> list[dict]:
    """Get sales over time grouped by period."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Determine grouping based on period
    if period == "daily":
        date_format = func.date(Listing.sold_at)
    elif period == "weekly":
        # SQLite doesn't have week function, approximate with date grouping
        date_format = func.date(Listing.sold_at, "weekday 0", "-6 days")
    else:  # monthly
        date_format = func.strftime("%Y-%m", Listing.sold_at)

    results = (
        db.query(
            date_format.label("period"),
            func.count(Listing.id).label("sales_count"),
            func.sum(Listing.sale_price).label("revenue"),
        )
        .filter(
            Listing.status == "sold", Listing.sold_at >= cutoff_date, Listing.sold_at.isnot(None)
        )
        .group_by("period")
        .order_by("period")
        .all()
    )

    return [
        {
            "period": str(row.period),
            "sales_count": row.sales_count,
            "revenue": float(row.revenue or 0),
        }
        for row in results
    ]


def get_listings_created_over_time(
    db: Session, period: str = "daily", days: int = 30
) -> list[dict]:
    """Get listings created over time grouped by period."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Determine grouping based on period
    if period == "daily":
        date_format = func.date(Listing.created_at)
    elif period == "weekly":
        date_format = func.date(Listing.created_at, "weekday 0", "-6 days")
    else:  # monthly
        date_format = func.strftime("%Y-%m", Listing.created_at)

    results = (
        db.query(
            date_format.label("period"),
            func.count(Listing.id).label("listings_count"),
        )
        .filter(Listing.created_at >= cutoff_date)
        .group_by("period")
        .order_by("period")
        .all()
    )

    return [
        {
            "period": str(row.period),
            "listings_count": row.listings_count,
        }
        for row in results
    ]


def get_best_sellers(db: Session, limit: int = 10) -> dict:
    """Get best-selling categories, brands, and items."""
    # Best-selling categories
    categories = (
        db.query(
            Listing.category,
            func.count(Listing.id).label("sales_count"),
            func.sum(Listing.sale_price).label("total_revenue"),
        )
        .filter(Listing.status == "sold", Listing.category.isnot(None))
        .group_by(Listing.category)
        .order_by(func.count(Listing.id).desc())
        .limit(limit)
        .all()
    )

    # Best-selling brands
    brands = (
        db.query(
            Listing.brand,
            func.count(Listing.id).label("sales_count"),
            func.sum(Listing.sale_price).label("total_revenue"),
        )
        .filter(Listing.status == "sold", Listing.brand.isnot(None))
        .group_by(Listing.brand)
        .order_by(func.count(Listing.id).desc())
        .limit(limit)
        .all()
    )

    # Most profitable items
    profitable_items = (
        db.query(
            Listing.id,
            Listing.title,
            Listing.category,
            Listing.brand,
            Listing.sale_price,
            Listing.initial_cost,
            (Listing.sale_price - Listing.initial_cost).label("profit"),
        )
        .filter(
            Listing.status == "sold",
            Listing.sale_price.isnot(None),
            Listing.initial_cost.isnot(None),
        )
        .order_by((Listing.sale_price - Listing.initial_cost).desc())
        .limit(limit)
        .all()
    )

    # Fastest-selling items (shortest time between posted_at and sold_at)
    fastest_items = (
        db.query(
            Listing.id,
            Listing.title,
            Listing.category,
            Listing.brand,
            Listing.posted_at,
            Listing.sold_at,
            (func.julianday(Listing.sold_at) - func.julianday(Listing.posted_at)).label(
                "days_to_sell"
            ),
        )
        .filter(
            Listing.status == "sold", Listing.posted_at.isnot(None), Listing.sold_at.isnot(None)
        )
        .order_by((func.julianday(Listing.sold_at) - func.julianday(Listing.posted_at)).asc())
        .limit(limit)
        .all()
    )

    return {
        "best_categories": [
            {
                "category": row.category,
                "sales_count": row.sales_count,
                "total_revenue": float(row.total_revenue or 0),
            }
            for row in categories
        ],
        "best_brands": [
            {
                "brand": row.brand,
                "sales_count": row.sales_count,
                "total_revenue": float(row.total_revenue or 0),
            }
            for row in brands
        ],
        "most_profitable": [
            {
                "id": row.id,
                "title": row.title,
                "category": row.category,
                "brand": row.brand,
                "sale_price": float(row.sale_price or 0),
                "initial_cost": float(row.initial_cost or 0),
                "profit": float(row.profit or 0),
            }
            for row in profitable_items
        ],
        "fastest_selling": [
            {
                "id": row.id,
                "title": row.title,
                "category": row.category,
                "brand": row.brand,
                "posted_at": row.posted_at.isoformat() if row.posted_at else None,
                "sold_at": row.sold_at.isoformat() if row.sold_at else None,
                "days_to_sell": round(row.days_to_sell, 1) if row.days_to_sell else None,
            }
            for row in fastest_items
        ],
    }


def get_inventory_value(db: Session) -> dict:
    """Get current inventory value breakdown."""
    # Total inventory value
    total_value = (
        db.query(
            func.sum(Listing.price).label("total_value"),
            func.count(Listing.id).label("total_items"),
        )
        .filter(Listing.status == "active", Listing.price.isnot(None))
        .first()
    )

    # Breakdown by category
    by_category = (
        db.query(
            Listing.category,
            func.sum(Listing.price).label("total_value"),
            func.count(Listing.id).label("items_count"),
            func.avg(Listing.price).label("avg_price"),
        )
        .filter(Listing.status == "active", Listing.price.isnot(None), Listing.category.isnot(None))
        .group_by(Listing.category)
        .order_by(func.sum(Listing.price).desc())
        .all()
    )

    # Average time to sell (for sold items)
    avg_time_to_sell = (
        db.query(
            func.avg(func.julianday(Listing.sold_at) - func.julianday(Listing.posted_at)).label(
                "avg_days"
            )
        )
        .filter(
            Listing.status == "sold", Listing.posted_at.isnot(None), Listing.sold_at.isnot(None)
        )
        .first()
    )

    avg_days = round(avg_time_to_sell.avg_days, 1) if avg_time_to_sell.avg_days else None

    return {
        "total_value": float(total_value.total_value or 0),
        "total_items": total_value.total_items,
        "avg_time_to_sell_days": avg_days,
        "by_category": [
            {
                "category": row.category,
                "total_value": float(row.total_value or 0),
                "items_count": row.items_count,
                "avg_price": float(row.avg_price or 0),
            }
            for row in by_category
        ],
    }
