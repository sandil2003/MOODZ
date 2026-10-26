"""Mood data routes for mood history, user facts, and mood statistics."""

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone, timedelta
from collections import Counter

from app.database import AsyncSessionLocal, get_db
from app.models import MoodHistory, UserFact
from app.schemas import MoodHistoryResponse, UserFactResponse


# ==========================================
# Router Definitions
# ==========================================
router = APIRouter(prefix="/mood-data", tags=["mood-data"])
mood_data_router = router  # alias for backwards compatibility


# ==========================================
# Mood Data Endpoints
# ==========================================

@router.get("/mood-history/{user_id}", response_model=List[MoodHistoryResponse])
async def get_mood_history(
    user_id: UUID,
    limit: int = Query(default=50, le=200),
    days: Optional[int] = Query(default=None, description="Filter by last N days")
):
    try:
        async with AsyncSessionLocal() as db:
            query = select(MoodHistory).where(
                MoodHistory.user_id == user_id
            ).order_by(desc(MoodHistory.created_at)).limit(limit)
            
            if days:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
                query = query.where(MoodHistory.created_at >= cutoff_date)
                
            result = await db.execute(query)
            mood_entries = result.scalars().all()
            return [
                MoodHistoryResponse(
                    id=entry.id,
                    user_id=entry.user_id,
                    mood_score=entry.mood_score,
                    sentiment_label=entry.sentiment_label,
                    topics=entry.topics if entry.topics else [],
                    summary=entry.summary,
                    session_id=entry.session_id,
                    created_at=entry.created_at
                )
                for entry in mood_entries
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-facts/{user_id}", response_model=List[UserFactResponse])
async def get_user_facts(
    user_id: UUID,
    category: Optional[str] = Query(default=None, description="Filter by category"),
    limit: int = Query(default=100, le=500)
):
    try:
        async with AsyncSessionLocal() as db:
            query = select(UserFact).where(
                UserFact.user_id == user_id
            ).order_by(desc(UserFact.created_at)).limit(limit)
            
            if category:
                query = query.where(UserFact.category == category)
                
            result = await db.execute(query)
            facts = result.scalars().all()
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
async def get_mood_stats(user_id: UUID, days: int = Query(default=30)):
    try:
        async with AsyncSessionLocal() as db:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            query = select(MoodHistory).where(
                MoodHistory.user_id == user_id,
                MoodHistory.created_at >= cutoff_date
            ).order_by(MoodHistory.created_at)
            
            result = await db.execute(query)
            mood_entries = result.scalars().all()
            
            if not mood_entries:
                return {
                    "total_entries": 0,
                    "average_mood": None,
                    "highest_mood": None,
                    "lowest_mood": None,
                    "most_common_sentiment": None,
                    "days_analyzed": days
                }
                
            mood_scores = [entry.mood_score for entry in mood_entries]
            sentiments = [entry.sentiment_label for entry in mood_entries if entry.sentiment_label]
            
            most_common_sentiment = None
            if sentiments:
                sentiment_counts = Counter(sentiments)
                most_common_sentiment = sentiment_counts.most_common(1)[0][0]
                
            return {
                "total_entries": len(mood_entries),
                "average_mood": round(sum(mood_scores) / len(mood_scores), 2),
                "highest_mood": max(mood_scores),
                "lowest_mood": min(mood_scores),
                "most_common_sentiment": most_common_sentiment,
                "days_analyzed": days,
                "trend": "improving" if len(mood_scores) > 1 and mood_scores[-1] > mood_scores[0] else "declining" if len(mood_scores) > 1 and mood_scores[-1] < mood_scores[0] else "stable"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
