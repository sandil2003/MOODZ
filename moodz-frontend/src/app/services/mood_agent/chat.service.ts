import { Injectable, signal } from '@angular/core';
import { v4 as uuidv4 } from 'uuid';

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    isStreaming?: boolean;
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
    classification?: {
        save: boolean;
        mood: string;
        extracted_facts: string[];
    };
    error?: string;
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

    // WebSocket for status updates
    private statusWebSocket: WebSocket | null = null;

    /**
     * Connect to WebSocket for deep search status updates
     */
    private connectStatusWebSocket() {
        if (this.statusWebSocket) {
            return; // Already connected
        }

        const wsUrl = `ws://localhost:8000/api/moods/chat/ws/status/${this.sessionId}`;
        this.statusWebSocket = new WebSocket(wsUrl);

        this.statusWebSocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'status') {
                    this.currentStatus.set(data.content);
                }
            } catch (e) {
                console.error('WebSocket message error:', e);
            }
        };

        this.statusWebSocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.statusWebSocket.onclose = () => {
            this.statusWebSocket = null;
        };
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
            this.connectStatusWebSocket();
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
                                // Streaming complete - add final message to history
                                const finalContent = this.currentStreamingMessage();
                                if (finalContent) {
                                    const finalMessage: ChatMessage = {
                                        id: assistantMessageId,
                                        role: 'assistant',
                                        content: finalContent,
                                        timestamp: new Date(),
                                        isStreaming: false
                                    };
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
}
