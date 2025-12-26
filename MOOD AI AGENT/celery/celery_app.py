from celery import Celery
from celery.schedules import crontab

app = Celery('mood_app', broker='redis://localhost:6379/0')

app.conf.beat_schedule = {
    'send daily mental health tip': {
        'task': 'mood_app.tasks.send_daily_tips',
        'schedule': crontab(hour=8, minute=0),
    },
    app.conf.timezone = 'UTC'
}
