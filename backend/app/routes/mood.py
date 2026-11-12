"""Mood data endpoints for user mood history, trends, and durable personal facts."""

from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.models import MoodHistory, UserFact
from app.schemas import MoodHistoryResponse, UserFactResponse

router = APIRouter(prefix="/mood-data", tags=["mood-data"])
mood_data_router = router  # Backwards compatibility alias


@router.get("/mood-history/{user_id}", response_model=List[MoodHistoryResponse])
async def get_mood_history(
    user_id: UUID,
    limit: int = Query(default=50, le=200),
    days: Optional[int] = Query(default=None, description="Filter to last N days"),
    db: AsyncSession = Depends(get_db)
) -> List[MoodHistoryResponse]:
    """Retrieve chronological mood check-ins and emotional scores for a user."""
    try:
        query = (
            select(MoodHistory)
            .where(MoodHistory.user_id == user_id)
            .order_by(desc(MoodHistory.created_at))
            .limit(limit)
        )
        if days:
            # Naive UTC datetime to match TIMESTAMP WITHOUT TIME ZONE in PostgreSQL
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
            query = query.where(MoodHistory.created_at >= cutoff)

        entries = (await db.execute(query)).scalars().all()
        return [
            MoodHistoryResponse(
                id=entry.id,
                user_id=entry.user_id,
                mood_score=entry.mood_score,
                sentiment_label=entry.sentiment_label,
                topics=entry.topics or [],
                summary=entry.summary,
                session_id=entry.session_id,
                created_at=entry.created_at
            )
            for entry in entries
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-facts/{user_id}", response_model=List[UserFactResponse])
async def get_user_facts(
    user_id: UUID,
    category: Optional[str] = Query(default=None, description="Filter by category tag"),
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db)
) -> List[UserFactResponse]:
    """Retrieve personal facts learned about the user across conversations."""
    try:
        query = (
            select(UserFact)
            .where(UserFact.user_id == user_id)
            .order_by(desc(UserFact.created_at))
            .limit(limit)
        )
        if category:
            query = query.where(UserFact.category == category)

        facts = (await db.execute(query)).scalars().all()
        return [
            UserFactResponse(
                id=fact.id,
                user_id=fact.user_id,
                fact_text=fact.fact_text,
                category=fact.category,
                source=fact.source,
                created_at=fact.created_at
            )
            for fact in facts
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mood-stats/{user_id}")
async def get_mood_stats(
    user_id: UUID,
    days: int = Query(default=30),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Calculate average mood score, distribution, and emotional trajectory."""
    try:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        query = (
            select(MoodHistory)
            .where(
                MoodHistory.user_id == user_id,
                MoodHistory.created_at >= cutoff
            )
            .order_by(MoodHistory.created_at)
        )
        entries = (await db.execute(query)).scalars().all()

        if not entries:
            return {
                "total_entries": 0,
                "average_mood": None,
                "highest_mood": None,
                "lowest_mood": None,
                "most_common_sentiment": None,
                "days_analyzed": days
            }

        scores = [e.mood_score for e in entries]
        sentiments = [e.sentiment_label for e in entries if e.sentiment_label]
        most_common_sentiment = Counter(sentiments).most_common(1)[0][0] if sentiments else None

        trend = "stable"
        if len(scores) > 1:
            if scores[-1] > scores[0]:
                trend = "improving"
            elif scores[-1] < scores[0]:
                trend = "declining"

        return {
            "total_entries": len(entries),
            "average_mood": round(sum(scores) / len(scores), 2),
            "highest_mood": max(scores),
            "lowest_mood": min(scores),
            "most_common_sentiment": most_common_sentiment,
            "days_analyzed": days,
            "trend": trend
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
