"""
Quick script to create a demo user in the database.
Run this once to create a user that the chat can use.
"""
import asyncio
import uuid
from app.database import AsyncSessionLocal
from app.models import User


async def create_demo_user():
    """Create a demo user for testing."""
    
    # This is the user_id from the error message
    user_id = uuid.UUID("c47209cb-b2f1-4c76-a7ae-19805f3926b4")
    
    async with AsyncSessionLocal() as db:
        # Check if user already exists
        from sqlalchemy import select
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"✅ User {user_id} already exists!")
            print(f"   Email: {existing_user.email}")
            print(f"   Name: {existing_user.name}")
            return
        
        # Create new user with all required fields
        user = User(
            id=user_id,
            email="demo@moodz.ai",
            name="Demo User",
            preferences={
                "tone": "friendly",
                "verbose": False
            },
            hashed_password="demo_password_hash",  # Not used for demo
            is_active=True,
            role="user"
        )
        
        db.add(user)
        await db.commit()
        
        print(f"✅ Created demo user!")
        print(f"   User ID: {user_id}")
        print(f"   Email: demo@moodz.ai")
        print(f"   Name: Demo User")
        print(f"\n🎉 You can now send messages in the chat!")
        print(f"   The mood history will save to this user.")


if __name__ == "__main__":
    asyncio.run(create_demo_user())
