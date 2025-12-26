import { Injectable, signal } from '@angular/core';
import { v4 as uuidv4 } from 'uuid';

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    isStreaming?: boolean;
    isCrisis?: boolean;
}

export interface ChatRequest {
    user_id: string;
    session_id: string;
    message: string;
    deep_search?: boolean;
}

export interface StreamChunk {
    chunk?: string;
    done?: boolean;
    session_id?: string;
    latency?: number;
    crisis_detected?: boolean;
    classification?: {
        save: boolean;
        mood: string;
        extracted_facts: string[];
    };
    error?: string;
}

export interface ChatSession {
    session_id: string;
    title: string;
    last_message_time: string;
    message_count: number;
    first_message?: string;
}

export interface ChatSessionDetail {
    session_id: string;
    messages: ChatMessage[];
    message_count: number;
}

@Injectable({
    providedIn: 'root'
})
export class ChatService {
    // API Configuration
    private readonly API_BASE_URL = 'http://localhost:8000';
    private readonly STREAM_ENDPOINT = '/api/moods/chat/stream';

    // IMPORTANT: Using the demo user that exists in the database
    // This is the user_id created by create_demo_user.py
    // For production, replace this with actual user authentication
    private readonly DEMO_USER_ID = 'c47209cb-b2f1-4c76-a7ae-19805f3926b4';

    // User and Session IDs
    private userId: string = this.DEMO_USER_ID;
    private sessionId: string = uuidv4();

    // Signals for reactive state management
    messages = signal<ChatMessage[]>([]);
    isStreaming = signal(false);
    error = signal<string | null>(null);
    currentStreamingMessage = signal<string>('');
    currentStatus = signal<string>('');  // For deep search status updates

    // Chat history signals
    chatSessions = signal<ChatSession[]>([]);
    currentSessionId = signal<string>(this.sessionId);

    // WebSocket for status updates
    private statusWebSocket: WebSocket | null = null;

    /**
     * Connect to WebSocket for deep search status updates
     */
    private connectStatusWebSocket(): Promise<void> {
        return new Promise((resolve, reject) => {
            if (this.statusWebSocket) {
                resolve(); // Already connected
                return;
            }

            const wsUrl = `ws://localhost:8000/api/moods/chat/ws/status/${this.sessionId}`;
            console.log('🔌 Connecting to WebSocket:', wsUrl);
            this.statusWebSocket = new WebSocket(wsUrl);

            this.statusWebSocket.onopen = () => {
                console.log('✅ WebSocket connected');
                resolve();
            };

            this.statusWebSocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('📨 WebSocket message:', data);
                    if (data.type === 'status') {
                        console.log('🔍 Status update:', data.content);
                        this.currentStatus.set(data.content);
                    }
                } catch (e) {
                    console.error('WebSocket message error:', e);
                }
            };

            this.statusWebSocket.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                reject(error);
            };

            this.statusWebSocket.onclose = () => {
                console.log('🔌 WebSocket disconnected');
                this.statusWebSocket = null;
            };

            // Timeout after 5 seconds
            setTimeout(() => {
                if (this.statusWebSocket?.readyState !== WebSocket.OPEN) {
                    reject(new Error('WebSocket connection timeout'));
                }
            }, 5000);
        });
    }

    /**
     * Disconnect WebSocket
     */
    private disconnectStatusWebSocket() {
        if (this.statusWebSocket) {
            this.statusWebSocket.close();
            this.statusWebSocket = null;
        }
        this.currentStatus.set('');
    }

    /**
     * Send a message and stream the response in real-time
     */
    async sendMessage(message: string, deepSearch: boolean = false): Promise<void> {
        if (!message.trim() || this.isStreaming()) {
            return;
        }

        // Clear previous errors and status
        this.error.set(null);
        this.currentStatus.set('');

        // Connect WebSocket if deep search is enabled
        if (deepSearch) {
            try {
                console.log('🔍 Deep search enabled, connecting WebSocket...');
                await this.connectStatusWebSocket();
                console.log('✅ WebSocket ready, proceeding with deep search');
            } catch (error) {
                console.error('❌ Failed to connect WebSocket:', error);
                this.error.set('Failed to connect for status updates');
            }
        }

        // Add user message to chat
        const userMessage: ChatMessage = {
            id: uuidv4(),
            role: 'user',
            content: message,
            timestamp: new Date()
        };
        this.messages.update(msgs => [...msgs, userMessage]);

        // Start streaming
        this.isStreaming.set(true);
        this.currentStreamingMessage.set('');

        // Create assistant message placeholder
        const assistantMessageId = uuidv4();
        // Commented out to prevent duplicate cards - streaming card will show instead
        // const assistantMessage: ChatMessage = {
        //     id: assistantMessageId,
        //     role: 'assistant',
        //     content: '',
        //     timestamp: new Date(),
        //     isStreaming: true
        // };
        // this.messages.update(msgs => [...msgs, assistantMessage]);

        try {
            await this.streamResponse(message, assistantMessageId, deepSearch);
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'An error occurred';
            this.error.set(errorMessage);

            // Remove the placeholder assistant message on error
            this.messages.update(msgs => msgs.filter(m => m.id !== assistantMessageId));
        } finally {
            this.isStreaming.set(false);
            this.currentStreamingMessage.set('');

            // Disconnect WebSocket after completion
            if (deepSearch) {
                this.disconnectStatusWebSocket();
            }
        }
    }

    /**
     * Stream response using Server-Sent Events
     */
    private async streamResponse(message: string, assistantMessageId: string, deepSearch: boolean = false): Promise<void> {
        const requestBody: ChatRequest = {
            user_id: this.userId,
            session_id: this.sessionId,
            message,
            deep_search: deepSearch
        };

        const response = await fetch(`${this.API_BASE_URL}${this.STREAM_ENDPOINT}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
            throw new Error('Response body is not readable');
        }

        const decoder = new TextDecoder();
        let buffer = '';

        try {
            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    break;
                }

                // Decode the chunk and add to buffer
                buffer += decoder.decode(value, { stream: true });

                // Process complete SSE messages
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // Keep incomplete line in buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6); // Remove 'data: ' prefix

                        try {
                            const parsed: StreamChunk = JSON.parse(data);

                            if (parsed.error) {
                                throw new Error(parsed.error);
                            }


                            if (parsed.chunk) {
                                // Append chunk to current streaming message
                                this.currentStreamingMessage.update(current => current + parsed.chunk);
                            }

                            if (parsed.done) {
                                console.log('🔍 Stream done event:', parsed);
                                console.log('🚨 Crisis detected flag:', parsed.crisis_detected);

                                // Streaming complete - add final message to history
                                const finalContent = this.currentStreamingMessage();
                                if (finalContent) {
                                    const finalMessage: ChatMessage = {
                                        id: assistantMessageId,
                                        role: 'assistant',
                                        content: finalContent,
                                        timestamp: new Date(),
                                        isStreaming: false,
                                        isCrisis: parsed.crisis_detected || false
                                    };
                                    console.log('💬 Final message:', finalMessage);
                                    this.messages.update(msgs => [...msgs, finalMessage]);
                                }

                                // Update session ID if provided
                                if (parsed.session_id) {
                                    this.sessionId = parsed.session_id;
                                }
                                break;
                            }
                        } catch (parseError) {
                            console.error('Error parsing SSE data:', parseError);
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }
    }

    /**
     * Clear all messages and start a new session
     */
    clearChat(): void {
        this.messages.set([]);
        this.sessionId = uuidv4();
        this.currentSessionId.set(this.sessionId);
        this.error.set(null);
        this.currentStreamingMessage.set('');
    }

    /**
     * Get current user ID (for debugging)
     */
    getUserId(): string {
        return this.userId;
    }

    /**
     * Get current session ID (for debugging)
     */
    getSessionId(): string {
        return this.sessionId;
    }

    /**
     * Load all chat sessions for the current user
     */
    async loadChatSessions(): Promise<void> {
        try {
            const response = await fetch(
                `${this.API_BASE_URL}/api/chat-history/sessions?user_id=${this.userId}`,
                {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const sessions: ChatSession[] = await response.json();
            this.chatSessions.set(sessions);
            console.log('✅ Loaded', sessions.length, 'chat sessions');
        } catch (error) {
            console.error('Error loading chat sessions:', error);
            this.error.set('Failed to load chat history');
        }
    }

    /**
     * Load a specific chat session and display its messages
     */
    async loadChatSession(sessionId: string): Promise<void> {
        try {
            const response = await fetch(
                `${this.API_BASE_URL}/api/chat-history/sessions/${sessionId}?user_id=${this.userId}`,
                {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const sessionDetail: ChatSessionDetail = await response.json();

            // Update messages with loaded session
            this.messages.set(sessionDetail.messages);

            // Update current session ID
            this.sessionId = sessionId;
            this.currentSessionId.set(sessionId);

            console.log('✅ Loaded session with', sessionDetail.message_count, 'messages');
        } catch (error) {
            console.error('Error loading chat session:', error);
            this.error.set('Failed to load chat session');
        }
    }

    /**
     * Start a new chat session
     */
    startNewChat(): void {
        this.messages.set([]);
        this.sessionId = uuidv4();
        this.currentSessionId.set(this.sessionId);
        this.error.set(null);
        this.currentStreamingMessage.set('');
        console.log('✨ Started new chat session:', this.sessionId);
    }
}
