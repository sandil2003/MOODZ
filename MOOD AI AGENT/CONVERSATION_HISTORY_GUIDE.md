# Accessing Conversation History

## Overview

Your MOOD AI Agent stores conversation history in multiple locations for different purposes. This guide shows you how to access stored conversations.

---

## Storage Locations

### 1. **Redis (Short-term Memory)**
- **Purpose**: Active session conversations
- **Duration**: 1 hour TTL (Time To Live)
- **Access**: Via API endpoints (see below)

### 2. **PostgreSQL (Long-term Storage)**
- **Purpose**: Mood history and user facts
- **Tables**: `mood_history`, `user_facts`
- **Access**: Direct database queries or future API endpoints

### 3. **Pinecone (Vector Database)**
- **Purpose**: Semantic search of conversations
- **Access**: Via vector similarity search

### 4. **JSONL Files (Logs)**
- **Purpose**: Debugging and analytics
- **Location**: Chat logs directory
- **Access**: Direct file reading

---

## New API Endpoints

I've created three new endpoints to access conversation history:

### 1. Get Session History

**Endpoint**: `GET /api/history/session/{session_id}`

**Parameters**:
- `session_id` (path): UUID of the session
- `limit` (query, optional): Max messages to retrieve (default: 50, max: 100)

**Example Request**:
```bash
curl http://localhost:8000/api/history/session/987fcdeb-51a2-43f7-b890-123456789abc?limit=20
```

**Response**:
```json
{
  "session_id": "987fcdeb-51a2-43f7-b890-123456789abc",
  "message_count": 15,
  "ttl_seconds": 3245,
  "messages": [
    {
      "role": "user",
      "content": "Hello, how are you?",
      "timestamp": "2025-12-09T14:20:00",
      "metadata": {}
    },
    {
      "role": "assistant",
      "content": "I'm doing well, thank you!",
      "timestamp": "2025-12-09T14:20:05",
      "metadata": {}
    }
  ]
}
```

### 2. List Active Sessions

**Endpoint**: `GET /api/history/sessions/active`

**Example Request**:
```bash
curl http://localhost:8000/api/history/sessions/active
```

**Response**:
```json
{
  "active_sessions": [
    "987fcdeb-51a2-43f7-b890-123456789abc",
    "123e4567-e89b-12d3-a456-426614174000"
  ],
  "count": 2
}
```

### 3. Clear Session History

**Endpoint**: `DELETE /api/history/session/{session_id}`

**Example Request**:
```bash
curl -X DELETE http://localhost:8000/api/history/session/987fcdeb-51a2-43f7-b890-123456789abc
```

**Response**:
```json
{
  "message": "Session cleared successfully",
  "session_id": "987fcdeb-51a2-43f7-b890-123456789abc"
}
```

---

## Frontend Integration

### Option 1: Add History Service

Create a service to fetch conversation history:

```typescript
// src/app/services/mood_agent/history.service.ts
import { Injectable, signal } from '@angular/core';

export interface SessionHistory {
  session_id: string;
  message_count: number;
  ttl_seconds: number;
  messages: Array<{
    role: string;
    content: string;
    timestamp: string;
    metadata: any;
  }>;
}

@Injectable({
  providedIn: 'root'
})
export class HistoryService {
  private readonly API_BASE_URL = 'http://localhost:8000';
  
  async getSessionHistory(sessionId: string, limit: number = 50): Promise<SessionHistory> {
    const response = await fetch(
      `${this.API_BASE_URL}/api/history/session/${sessionId}?limit=${limit}`
    );
    
    if (!response.ok) {
      throw new Error(`Failed to fetch history: ${response.status}`);
    }
    
    return await response.json();
  }
  
  async getActiveSessions(): Promise<string[]> {
    const response = await fetch(
      `${this.API_BASE_URL}/api/history/sessions/active`
    );
    
    if (!response.ok) {
      throw new Error(`Failed to fetch sessions: ${response.status}`);
    }
    
    const data = await response.json();
    return data.active_sessions;
  }
  
  async clearSession(sessionId: string): Promise<void> {
    const response = await fetch(
      `${this.API_BASE_URL}/api/history/session/${sessionId}`,
      { method: 'DELETE' }
    );
    
    if (!response.ok) {
      throw new Error(`Failed to clear session: ${response.status}`);
    }
  }
}
```

### Option 2: Load History on Component Init

Modify the chat component to load previous messages:

```typescript
// In mood-agent.ts
async ngOnInit() {
  const sessionId = this.chatService.getSessionId();
  
  try {
    const history = await this.historyService.getSessionHistory(sessionId);
    
    // Convert to ChatMessage format and load into service
    const messages = history.messages.map(msg => ({
      id: uuidv4(),
      role: msg.role as 'user' | 'assistant',
      content: msg.content,
      timestamp: new Date(msg.timestamp)
    }));
    
    this.chatService.messages.set(messages);
  } catch (error) {
    console.error('Failed to load history:', error);
  }
}
```

---

## Testing the Endpoints

### Using Browser DevTools

Open the browser console and run:

```javascript
// Get session ID from chat service
const sessionId = '987fcdeb-51a2-43f7-b890-123456789abc';

// Fetch history
fetch(`http://localhost:8000/api/history/session/${sessionId}`)
  .then(res => res.json())
  .then(data => console.log('History:', data));

// List active sessions
fetch('http://localhost:8000/api/history/sessions/active')
  .then(res => res.json())
  .then(data => console.log('Active sessions:', data));
```

### Using Swagger UI

1. Navigate to `http://localhost:8000/docs`
2. Find the **history** section
3. Try out the endpoints interactively

---

## Direct Database Access

### PostgreSQL - Mood History

```sql
-- Get all mood entries for a user
SELECT * FROM mood_history 
WHERE user_id = '123e4567-e89b-12d3-a456-426614174000'
ORDER BY created_at DESC
LIMIT 20;

-- Get mood entries for a specific session
SELECT * FROM mood_history 
WHERE session_id = '987fcdeb-51a2-43f7-b890-123456789abc'
ORDER BY created_at DESC;
```

### PostgreSQL - User Facts

```sql
-- Get all extracted facts for a user
SELECT * FROM user_facts 
WHERE user_id = '123e4567-e89b-12d3-a456-426614174000'
ORDER BY created_at DESC;
```

### Redis - Session Data

```bash
# Connect to Redis
redis-cli

# List all session keys
KEYS session:*

# Get session messages
LRANGE session:987fcdeb-51a2-43f7-b890-123456789abc 0 -1

# Get session length
LLEN session:987fcdeb-51a2-43f7-b890-123456789abc

# Get session TTL
TTL session:987fcdeb-51a2-43f7-b890-123456789abc
```

---

## Files Created

- **Backend**: [history.py](file:///C:/Users/sandi/Documents/AI/MOODZ/MOOD%20AI%20AGENT/app/routes/history.py) - New API endpoints
- **Backend**: [main.py](file:///C:/Users/sandi/Documents/AI/MOODZ/MOOD%20AI%20AGENT/main.py) - Router registration

---

## Next Steps

1. **Test the endpoints** using Swagger UI or curl
2. **Create HistoryService** in Angular (optional)
3. **Add "Load Previous Chat" button** to UI (optional)
4. **Implement session selector** to switch between conversations (optional)

The conversation history is now fully accessible via API! 🎉
