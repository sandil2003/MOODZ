import { Component, inject, signal, effect, ElementRef, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ChatService, ChatMessage } from '../../services/mood_agent/chat.service';

@Component({
  selector: 'app-mood-agent',
  imports: [CommonModule, FormsModule],
  templateUrl: './mood-agent.html',
  styleUrl: './mood-agent.css',
})
export class MoodAgent {
  private chatService = inject(ChatService);

  // Signals from service
  messages = this.chatService.messages;
  isStreaming = this.chatService.isStreaming;
  error = this.chatService.error;

  // Local component state
  userInput = signal('');

  // Reference to messages container for auto-scroll
  messagesContainer = viewChild<ElementRef>('messagesContainer');

  constructor() {
    // Auto-scroll when new messages arrive
    effect(() => {
      const msgs = this.messages();
      if (msgs.length > 0) {
        this.scrollToBottom();
      }
    });
  }

  /**
   * Send message to chat service
   */
  async sendMessage(): Promise<void> {
    const message = this.userInput().trim();
    if (!message || this.isStreaming()) {
      return;
    }

    // Clear input immediately
    this.userInput.set('');

    // Send message
    await this.chatService.sendMessage(message);
  }

  /**
   * Handle Enter key press (send message)
   */
  onKeyPress(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  /**
   * Clear all messages
   */
  clearChat(): void {
    this.chatService.clearChat();
  }

  /**
   * Scroll to bottom of messages container
   */
  private scrollToBottom(): void {
    setTimeout(() => {
      const container = this.messagesContainer()?.nativeElement;
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    }, 0);
  }

  /**
   * Track messages by ID for performance
   */
  trackByMessageId(index: number, message: ChatMessage): string {
    return message.id;
  }
}
