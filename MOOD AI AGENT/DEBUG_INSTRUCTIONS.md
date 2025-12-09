# Debug Instructions

## I've Added Detailed Logging

The backend will now print detailed information when saving conversations. 

## What to Do Now

### Step 1: Send a Test Message
1. Go to: `http://localhost:4200/mood-agent`
2. Send this message:
   ```
   I'm feeling really stressed about my presentation tomorrow. I've been working on it all week but I'm still worried about how it will go.
   ```
3. Wait for the AI response to complete

### Step 2: Check the Backend Terminal
Look at the terminal where `python main.py` is running. You should see output like this:

```
============================================================
SAVE_CONVERSATION_INTELLIGENTLY CALLED
============================================================
User ID: xxxxx-xxxx-xxxx-xxxx-xxxxxxxxx
Session ID: xxxxx-xxxx-xxxx-xxxx-xxxxxxxxx
Message: I'm feeling really stressed...
Classification: {'save': True, 'mood': 'stressed', 'extracted_facts': []}
============================================================

✅ Classifier said SAVE=TRUE, proceeding with save...
📝 Saving user message to Pinecone...
✅ User message saved to Pinecone
📝 Saving assistant response to Pinecone...
✅ Assistant response saved to Pinecone
ℹ️  No facts extracted from this message
📊 Detected mood: stressed
💾 Saving mood to PostgreSQL...
   Mood score: 3/10
✅ Saved mood 'stressed' (score: 3) to PostgreSQL

============================================================
SAVE COMPLETED SUCCESSFULLY
============================================================
```

### Step 3: What the Logs Tell You

**If you see:**
- ✅ `SAVE_CONVERSATION_INTELLIGENTLY CALLED` → Function is running
- ✅ `Classifier said SAVE=TRUE` → Classifier is working
- ✅ `Saved mood 'stressed' to PostgreSQL` → Database save succeeded
- ❌ `Skipping database save - classifier said save=False` → Message was too generic
- ❌ `Mood is neutral - NOT saving to database` → Neutral moods aren't saved
- ❌ `ERROR SAVING CONVERSATION` → There's a database/connection error

### Step 4: Check Mood History Page
After seeing successful save logs, go to:
`http://localhost:4200/mood-history`

You should now see your mood entry!

## Common Issues

### If you see "save=False":
- The message was too generic (like "hello")
- Try a more emotional/personal message

### If you see "Mood is neutral":
- The classifier detected neutral mood
- Neutral moods aren't saved to reduce database bloat
- Try a message with clear emotion (happy, sad, stressed, etc.)

### If you see errors:
- Check PostgreSQL is running
- Check database connection in `.env` file
- Share the error message with me

## Next Steps
1. Send the test message
2. Check the backend terminal output
3. Report what you see!
