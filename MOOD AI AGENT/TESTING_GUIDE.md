# Testing Guide: Verify Mood History System

## Current Status
✅ Backend API is working  
✅ Frontend is loading correctly  
❌ **No data in database yet**

## Why No Data?

The database is empty because:
1. You haven't sent any messages in the chat yet, OR
2. The messages sent were too generic (like "Hello") and the classifier decided not to save them

## How to Test (Step-by-Step)

### Step 1: Send a Meaningful Message
1. Go to: `http://localhost:4200/mood-agent`
2. Type this exact message:
   ```
   I'm feeling really stressed about my presentation tomorrow. I've been working on it all week but I'm still worried.
   ```
3. Press Enter or click Send
4. **Wait for the AI response to complete** (important!)

### Step 2: Check the Mood History Page
1. Go to: `http://localhost:4200/mood-history`
2. You should now see:
   - Statistics showing 1 entry
   - A timeline item with your mood
   - Mood score around 3-4/10
   - Sentiment: "anxious" or "stressed"

### Step 3: Send a Message with Personal Info
1. Go back to: `http://localhost:4200/mood-agent`
2. Send this message:
   ```
   I just adopted a golden retriever puppy named Max! He's 3 months old and I love taking him to the park.
   ```
3. Wait for response

### Step 4: Check Facts Were Extracted
1. Refresh: `http://localhost:4200/mood-history`
2. You should now see in "Things I Know About You":
   - "User has a golden retriever puppy named Max"
   - "User's dog is 3 months old"
   - Other extracted facts

## What NOT to Send

These messages will NOT be saved (too generic):
- ❌ "Hello"
- ❌ "How are you?"
- ❌ "Thanks"
- ❌ "OK"

## Troubleshooting

### If still no data after sending messages:

1. **Check browser console** (F12) for errors
2. **Check backend logs** in the terminal running `python main.py`
3. **Verify the backend restarted** after we added the mood_data routes

### Quick API Test

Open browser and go to:
```
http://localhost:8000/docs
```

Try the `/api/mood-data/mood-history/{user_id}` endpoint with your user_id.

---

## Next Steps

1. Send the stress message in the chat
2. Wait for AI response
3. Check mood history page
4. Report what you see!
