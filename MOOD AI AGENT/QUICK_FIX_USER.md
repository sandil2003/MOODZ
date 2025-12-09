# Quick Fix: Create Demo User

## The Problem
The chat is trying to save data for a user that doesn't exist in the database, causing this error:
```
Key (user_id)=(c47209cb-b2f1-4c76-a7ae-19805f3926b4) is not present in table "users"
```

## Solution: Run This SQL Query

Open your PostgreSQL query tool (pgAdmin, DBeaver, etc.) and run this:

```sql
INSERT INTO users (id, email, name, preferences, hashed_password, is_active, role, created_at, last_active)
VALUES (
    'c47209cb-b2f1-4c76-a7ae-19805f3926b4'::uuid,
    'demo@moodz.ai',
    'Demo User',
    '{"tone": "friendly", "verbose": false}'::jsonb,
    'demo_password_hash',
    true,
    'user',
    NOW(),
    NOW()
);
```

## After Running the SQL

1. ✅ The demo user will exist in the database
2. ✅ Send a message in the chat at `http://localhost:4200/mood-agent`
3. ✅ Check `http://localhost:4200/mood-history` - your data will appear!

## Test Message

Send this in the chat:
```
I just adopted a golden retriever puppy named Max! He's 3 months old and I love taking him to the park.
```

You should see:
- ✅ Mood saved (happy/excited)
- ✅ Facts extracted about Max
- ✅ Data appears in mood history page

That's it! The foreign key error will be resolved. 🎉
