import resend 
from app.database import SessionLocal
from app.models import User
from .celery_app import app

@app.task(name="app.tasks.send_daily_tips")
def send_daily_tips():
    # Because Celery is sync, we use asyncio.run to call our async logic
    asyncio.run(process_tips())

async def process_tips():
    async with AsyncSessionLocal() as db:
        # Fetching data asynchronously
        result = await db.execute(select(User).where(User.wants_tips == True))
        users = result.scalars().all()
        
        for user in users:
            send_individual_email.delay(user.email, "Keep breathing!")
        db.close()
        