import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MoodDataService, MoodHistoryEntry, UserFact, MoodStats } from '../../services/mood_agent/mood-data.service';
import { ChatService } from '../../services/mood_agent/chat.service';
import { MarkdownComponent, MarkdownModule } from 'ngx-markdown';

@Component({
  selector: 'app-mood-history',
  imports: [CommonModule, FormsModule, MarkdownModule],
  templateUrl: './mood-history.html',
  styleUrl: './mood-history.css',
})
export class MoodHistory implements OnInit {
  private moodDataService = inject(MoodDataService);
  private chatService = inject(ChatService);

  // Signals for data
  moodHistory = signal<MoodHistoryEntry[]>([]);
  userFacts = signal<UserFact[]>([]);
  moodStats = signal<MoodStats | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);

  // Filter options
  daysFilter = signal(30);
  selectedCategory = signal<string | null>(null);

  async ngOnInit() {
    await this.loadData();
  }

  async loadData() {
    this.loading.set(true);
    this.error.set(null);

    try {
      const userId = this.chatService.getUserId();
      const days = this.daysFilter();

      // Load all data in parallel
      const [history, facts, stats] = await Promise.all([
        this.moodDataService.getMoodHistory(userId, 50, days),
        this.moodDataService.getUserFacts(userId, this.selectedCategory() || undefined),
        this.moodDataService.getMoodStats(userId, days)
      ]);

      this.moodHistory.set(history);
      this.userFacts.set(facts);
      this.moodStats.set(stats);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load data';
      this.error.set(errorMessage);
    } finally {
      this.loading.set(false);
    }
  }

  async changeDaysFilter(days: number) {
    this.daysFilter.set(days);
    await this.loadData();
  }

  async changeCategoryFilter(category: string | null) {
    this.selectedCategory.set(category);
    await this.loadData();
  }

  getMoodColor(score: number): string {
    if (score >= 8) return '#10b981'; // green
    if (score >= 6) return '#3b82f6'; // blue
    if (score >= 4) return '#f59e0b'; // orange
    return '#ef4444'; // red
  }

  getMoodEmoji(score: number): string {
    if (score >= 9) return '😄';
    if (score >= 7) return '😊';
    if (score >= 5) return '😐';
    if (score >= 3) return '😔';
    return '😢';
  }

  getTrendIcon(trend: string): string {
    if (trend === 'improving') return '📈';
    if (trend === 'declining') return '📉';
    return '➡️';
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  trackByMoodId(index: number, item: MoodHistoryEntry): number {
    return item.id;
  }

  trackByFactId(index: number, item: UserFact): number {
    return item.id;
  }
}
