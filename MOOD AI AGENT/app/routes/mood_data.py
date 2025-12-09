from fastapi import APIRouter, HTTPException, Query
from uuid import UUID
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from app.database import AsyncSessionLocal
from app.models import MoodHistory, UserFact
from sqlalchemy import select, desc

router = APIRouter(prefix="/mood-data", tags=["mood-data"])


class MoodHistoryResponse(BaseModel):
    """Response schema for mood history entry."""
    id: int
    user_id: str
    mood_score: int
    sentiment_label: Optional[str]
    topics: Optional[List[str]]
    summary: str
    session_id: Optional[str]
    created_at: str


class UserFactResponse(BaseModel):
    """Response schema for user fact."""
    id: int
    user_id: str
    fact_text: str
    category: str
    source: str
    created_at: str


@router.get("/mood-history/{user_id}", response_model=List[MoodHistoryResponse])
async def get_mood_history(
    user_id: UUID,
    limit: int = Query(default=50, le=200),
    days: Optional[int] = Query(default=None, description="Filter by last N days")
):
    """
    Get mood history for a specific user.
    
    Args:
        user_id: User UUID
        limit: Maximum number of entries to return (max 200)
        days: Optional filter for last N days
    
    Returns:
        List[MoodHistoryResponse]: List of mood history entries
    """
    try:
        async with AsyncSessionLocal() as db:
            # Build query
            query = select(MoodHistory).where(
                MoodHistory.user_id == user_id
            ).order_by(desc(MoodHistory.created_at)).limit(limit)
            
            # Add date filter if specified
            if days:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                query = query.where(MoodHistory.created_at >= cutoff_date)
            
            # Execute query
            result = await db.execute(query)
            mood_entries = result.scalars().all()
            
            # Convert to response model
            return [
                MoodHistoryResponse(
                    id=entry.id,
                    user_id=str(entry.user_id),
                    mood_score=entry.mood_score,
                    sentiment_label=entry.sentiment_label,
                    topics=entry.topics if entry.topics else [],
                    summary=entry.summary,
                    session_id=str(entry.session_id) if entry.session_id else None,
                    created_at=entry.created_at.isoformat()
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
    """
    Get user facts for a specific user.
    
    Args:
        user_id: User UUID
        category: Optional category filter
        limit: Maximum number of facts to return (max 500)
    
    Returns:
        List[UserFactResponse]: List of user facts
    """
    try:
        async with AsyncSessionLocal() as db:
            # Build query
            query = select(UserFact).where(
                UserFact.user_id == user_id
            ).order_by(desc(UserFact.created_at)).limit(limit)
            
            # Add category filter if specified
            if category:
                query = query.where(UserFact.category == category)
            
            # Execute query
            result = await db.execute(query)
            facts = result.scalars().all()
            
            # Convert to response model
            return [
                UserFactResponse(
                    id=fact.id,
                    user_id=str(fact.user_id),
                    fact_text=fact.fact_text,
                    category=fact.category,
                    source=fact.source,
                    created_at=fact.created_at.isoformat()
                )
                for fact in facts
            ]
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mood-stats/{user_id}")
async def get_mood_stats(user_id: UUID, days: int = Query(default=30)):
    """
    Get mood statistics for a user.
    
    Args:
        user_id: User UUID
        days: Number of days to analyze (default: 30)
    
    Returns:
        dict: Mood statistics including average, trends, etc.
    """
    try:
        async with AsyncSessionLocal() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
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
            
            # Calculate statistics
            mood_scores = [entry.mood_score for entry in mood_entries]
            sentiments = [entry.sentiment_label for entry in mood_entries if entry.sentiment_label]
            
            # Find most common sentiment
            most_common_sentiment = None
            if sentiments:
                from collections import Counter
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
