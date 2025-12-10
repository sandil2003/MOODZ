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
  currentStreamingMessage = this.chatService.currentStreamingMessage;
  currentStatus = this.chatService.currentStatus;

  // Local component state
  userInput = signal('');
  deepSearchEnabled = signal(false);
  notesEnabled = signal(false);

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

  // Send message
  async sendMessage() {
    const message = this.userInput().trim();
    if (!message || this.isStreaming()) {
      return;
    }

    // Clear input
    this.userInput.set('');

    // Send through chat service with deep search flag
    await this.chatService.sendMessage(message, this.deepSearchEnabled());
  }

  // Handle Enter key
  onKeyPress(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  // Clear chat
  clearChat() {
    this.chatService.clearChat();
  }

  // Toggle deep search
  toggleDeepSearch() {
    this.deepSearchEnabled.update(enabled => !enabled);
    console.log('Deep Search:', this.deepSearchEnabled() ? 'Enabled' : 'Disabled');
  }

  // Toggle notes
  toggleNotes() {
    this.notesEnabled.update(enabled => !enabled);
    console.log('Notes:', this.notesEnabled() ? 'Enabled' : 'Disabled');
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
