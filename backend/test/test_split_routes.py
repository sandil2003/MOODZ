"""Test split routes for chat, history, and mood."""

import os
import sys

# Ensure backend root is on sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_routes_import():
    print("Testing routes imports...")
    
    # Test importing from app.routes
    from app.routes import chat, history, mood, health, auth
    print("✅ Successfully imported chat, history, mood, health, auth from app.routes")
    
    # 1. Test chat route components
    from app.routes.chat import (
        router as chat_router_default,
        chat_router,
        normalize_text,
        ConnectionManager,
        manager,
        save_chat_message_to_db,
        save_conversation_intelligently,
        stream_chat_response,
        chat_stream,
        chat as chat_endpoint,
        websocket_status
    )
    assert chat_router_default is chat_router
    assert chat_router.prefix == "/moods/chat"
    
    chat_route_paths = [route.path for route in chat_router.routes]
    print(f"Chat route paths: {chat_route_paths}")
    assert "/moods/chat/stream" in chat_route_paths
    assert "/moods/chat/" in chat_route_paths
    assert "/moods/chat/ws/status/{session_id}" in chat_route_paths
    print("✅ Chat router endpoints verified")
    
    # 2. Test history route components
    from app.routes.history import (
        router as history_router_default,
        history_router,
        chat_history_router,
        SessionHistoryResponse,
        get_chat_sessions,
        get_chat_session,
        get_redis_session_history,
        get_active_sessions,
        clear_session_history
    )
    assert chat_history_router.prefix == "/chat-history"
    assert history_router.prefix == "/history"
    
    chat_hist_paths = [route.path for route in chat_history_router.routes]
    print(f"Chat history route paths: {chat_hist_paths}")
    assert "/chat-history/sessions" in chat_hist_paths
    assert "/chat-history/sessions/{session_id}" in chat_hist_paths
    
    redis_hist_paths = [route.path for route in history_router.routes]
    print(f"Redis history route paths: {redis_hist_paths}")
    assert "/history/session/{session_id}" in redis_hist_paths
    assert "/history/sessions/active" in redis_hist_paths
    print("✅ History router endpoints verified")
    
    # 3. Test mood route components
    from app.routes.mood import (
        router as mood_router_default,
        mood_data_router,
        get_mood_history,
        get_user_facts,
        get_mood_stats
    )
    assert mood_router_default is mood_data_router
    assert mood_data_router.prefix == "/mood-data"
    
    mood_paths = [route.path for route in mood_data_router.routes]
    print(f"Mood route paths: {mood_paths}")
    assert "/mood-data/mood-history/{user_id}" in mood_paths
    assert "/mood-data/user-facts/{user_id}" in mood_paths
    assert "/mood-data/mood-stats/{user_id}" in mood_paths
    print("✅ Mood router endpoints verified")
    
    # 4. Test backwards compatibility re-exports from app.routes.chat
    from app.routes.chat import (
        history_router as compat_history_router,
        chat_history_router as compat_chat_history_router,
        mood_data_router as compat_mood_data_router
    )
    assert compat_history_router is history_router
    assert compat_chat_history_router is chat_history_router
    assert compat_mood_data_router is mood_data_router
    print("✅ Backwards compatibility re-exports verified")
    
    # 5. Test main FastAPI application route registration
    from main import app
    openapi_schema = app.openapi()
    all_app_routes = list(openapi_schema["paths"].keys())
    print(f"Total OpenAPI paths in app: {len(all_app_routes)}")
    
    expected_endpoints = [
        "/api/moods/chat/stream",
        "/api/moods/chat/",
        "/api/chat-history/sessions",
        "/api/chat-history/sessions/{session_id}",
        "/api/history/session/{session_id}",
        "/api/history/sessions/active",
        "/api/mood-data/mood-history/{user_id}",
        "/api/mood-data/user-facts/{user_id}",
        "/api/mood-data/mood-stats/{user_id}",
        "/health/",
        "/health/db",
        "/health/redis",
        "/api/auth/register",
        "/api/auth/login"
    ]
    
    for endpoint in expected_endpoints:
        assert endpoint in all_app_routes, f"Missing route: {endpoint}"
        print(f"  Verified route: {endpoint}")
        
    print("✅ All application routes properly mounted under /api!")


if __name__ == "__main__":
    test_routes_import()
    print("\n🎉 ALL ROUTE SPLIT TESTS PASSED SUCCESSFULLY!")
