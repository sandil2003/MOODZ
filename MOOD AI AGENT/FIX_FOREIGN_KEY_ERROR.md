# Fix for Foreign Key Error

## Problem Found! 🎯

The error message shows:
```
Key (user_id)=(c47209cb-b2f1-4c76-a7ae-19805f3926b4) is not present in table "users"
```

**The issue**: The chat is using a user_id that doesn't exist in the database. When trying to save mood history or facts, it fails because of the foreign key constraint.

## Solution

Run this command in a **NEW terminal** (keep the backend running):

```powershell
cd "C:\Users\sandi\Documents\AI\MOODZ\MOOD AI AGENT"
python create_demo_user.py
```

This will create a demo user in the database with the exact user_id that the chat is using.

## What This Does

1. Creates a user record with ID: `c47209cb-b2f1-4c76-a7ae-19805f3926b4`
2. Sets email: `demo@moodz.ai`
3. Sets name: `Demo User`
4. Allows mood history and facts to be saved

## After Running the Script

1. ✅ The user will exist in the database
2. ✅ Foreign key constraints will be satisfied
3. ✅ Mood history will save successfully
4. ✅ User facts will save successfully

Then try sending a message again in the chat!

## Alternative: Use pgAdmin or SQL

If you prefer, you can also create the user directly in PostgreSQL:

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

## Long-term Solution

For production, you'll want to implement proper user registration/authentication so users are created when they sign up. For now, this demo user will work perfectly for testing!
