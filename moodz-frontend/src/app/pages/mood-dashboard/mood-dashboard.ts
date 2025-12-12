import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MoodDataService, type MoodHistoryEntry, type UserFact, type MoodStats } from '../../services/mood_agent/mood-data.service';
import { ChatService } from '../../services/mood_agent/chat.service';

// Interfaces for type safety
interface MoodEntry {
  id: number;
  title: string;
  score: number;
  maxScore: number;
  timestamp: string;
  description: string;
  type: 'anxious' | 'down' | 'positive';
}

interface Insight {
  id: number;
  text: string;
  source: string;
  date: string;
}

interface SentimentData {
  label: string;
  badge: string;
  description: string;
}

@Component({
  selector: 'app-mood-dashboard',
  imports: [CommonModule],
  templateUrl: './mood-dashboard.html',
  styleUrl: './mood-dashboard.css',
})
export class MoodDashboard implements OnInit {
  // Inject services
  private moodDataService = inject(MoodDataService);
  private chatService = inject(ChatService);

  // State management signals
  isLoading = signal<boolean>(true);
  error = signal<string | null>(null);

  // Data signals
  averageScore = signal<number>(0);
  maxScore = signal<number>(10);
  sentiment = signal<SentimentData>({
    label: 'Loading...',
    badge: 'NEUTRAL',
    description: 'Analyzing your recent emotional landscape...'
  });
  insights = signal<Insight[]>([]);
  moodEntries = signal<MoodEntry[]>([]);

  async ngOnInit() {
    await this.loadDashboardData();
  }

  /**
   * Load all dashboard data from backend
   */
  private async loadDashboardData() {
    try {
      this.isLoading.set(true);
      this.error.set(null);

      const userId = this.chatService.getUserId();

      // Fetch all data in parallel
      const [moodHistory, userFacts, moodStats] = await Promise.all([
        this.moodDataService.getMoodHistory(userId, 10, 7), // Last 10 entries, 7 days
        this.moodDataService.getUserFacts(userId, undefined, 3), // Top 3 facts
        this.moodDataService.getMoodStats(userId, 7) // Last 7 days stats
      ]);

      // Transform and update signals
      this.updateMoodEntries(moodHistory);
      this.updateInsights(userFacts);
      this.updateStats(moodStats);

    } catch (err) {
      this.error.set('Failed to load dashboard data. Please try again.');
      console.error('Dashboard load error:', err);

      // Set default values on error
      this.setDefaultValues();
    } finally {
      this.isLoading.set(false);
    }
  }

  /**
   * Retry loading data
   */
  async retryLoad() {
    await this.loadDashboardData();
  }

  /**
   * Transform mood history entries from backend to UI format
   */
  private updateMoodEntries(entries: MoodHistoryEntry[]) {
    const transformedEntries: MoodEntry[] = entries.map(entry => ({
      id: entry.id,
      title: this.generateMoodTitle(entry.sentiment_label, entry.mood_score),
      score: entry.mood_score,
      maxScore: 10,
      timestamp: this.formatTimestamp(entry.created_at),
      description: `"${entry.summary}"`,
      type: this.mapSentimentToType(entry.sentiment_label)
    }));

    this.moodEntries.set(transformedEntries);
  }

  /**
   * Transform user facts from backend to UI format
   */
  private updateInsights(facts: UserFact[]) {
    const transformedInsights: Insight[] = facts.map(fact => ({
      id: fact.id,
      text: fact.fact_text,
      source: fact.source.toUpperCase().replace('_', ' '),
      date: this.formatDate(fact.created_at)
    }));

    this.insights.set(transformedInsights);
  }

  /**
   * Update stats (average score and sentiment)
   */
  private updateStats(stats: MoodStats) {
    // Update average score
    this.averageScore.set(stats.average_mood || 0);

    // Update sentiment
    const sentimentLabel = stats.most_common_sentiment || 'Mixed';
    this.sentiment.set({
      label: sentimentLabel,
      badge: this.mapSentimentToBadge(stats.most_common_sentiment),
      description: this.generateSentimentDescription(stats)
    });
  }

  /**
   * Set default values when data fails to load
   */
  private setDefaultValues() {
    this.averageScore.set(0);
    this.sentiment.set({
      label: 'No Data',
      badge: 'NEUTRAL',
      description: 'No mood data available yet. Start chatting to track your mood!'
    });
    this.insights.set([]);
    this.moodEntries.set([]);
  }

  /**
   * Generate mood title from sentiment and score
   */
  private generateMoodTitle(sentiment: string | null, score: number): string {
    if (!sentiment) {
      return score >= 7 ? 'Feeling Good' : score >= 4 ? 'Neutral Mood' : 'Feeling Down';
    }

    const sentimentMap: Record<string, string> = {
      'Anxious': 'Feeling Anxious',
      'Stressed': 'Feeling Stressed',
      'Angry': 'Feeling Angry',
      'Sad': 'A Bit Down',
      'Happy': 'Feeling Happy',
      'Excited': 'Feeling Excited',
      'Content': 'Feeling Content',
      'Calm': 'Feeling Calm',
      'Neutral': 'Neutral Mood'
    };

    return sentimentMap[sentiment] || `Feeling ${sentiment}`;
  }

  /**
   * Map sentiment to mood type for color coding
   */
  private mapSentimentToType(sentiment: string | null): 'anxious' | 'down' | 'positive' {
    if (!sentiment) return 'down';

    const anxiousTypes = ['Anxious', 'Stressed', 'Angry'];
    const downTypes = ['Sad', 'Neutral'];
    const positiveTypes = ['Happy', 'Excited', 'Content', 'Calm'];

    if (anxiousTypes.includes(sentiment)) return 'anxious';
    if (downTypes.includes(sentiment)) return 'down';
    if (positiveTypes.includes(sentiment)) return 'positive';

    return 'down'; // Default
  }

  /**
   * Map sentiment to badge text
   */
  private mapSentimentToBadge(sentiment: string | null): string {
    if (!sentiment) return 'NEUTRAL';

    const positiveTypes = ['Happy', 'Excited', 'Content', 'Calm'];
    const negativeTypes = ['Sad', 'Anxious', 'Stressed', 'Angry'];
    const neutralTypes = ['Neutral'];

    if (positiveTypes.includes(sentiment)) return 'POSITIVE';
    if (negativeTypes.includes(sentiment)) return 'NEGATIVE';
    if (neutralTypes.includes(sentiment)) return 'NEUTRAL';

    return 'MIXED';
  }

  /**
   * Generate sentiment description from stats
   */
  private generateSentimentDescription(stats: MoodStats): string {
    if (stats.total_entries === 0) {
      return 'No mood entries yet. Start tracking your emotional journey!';
    }

    const trend = stats.trend;
    const sentiment = stats.most_common_sentiment;

    if (trend === 'improving') {
      return `Your mood is trending upward! ${sentiment ? `Predominantly ${sentiment.toLowerCase()} in recent entries.` : ''}`;
    } else if (trend === 'declining') {
      return `Your mood has been declining. ${sentiment ? `Mostly ${sentiment.toLowerCase()} lately.` : ''} Consider reaching out for support.`;
    } else {
      return `Your mood has been stable. ${sentiment ? `Predominantly ${sentiment.toLowerCase()} in recent entries.` : ''}`;
    }
  }

  /**
   * Format ISO timestamp to readable format (e.g., "Dec 9, 09:30 AM")
   */
  private formatTimestamp(isoString: string): string {
    const date = new Date(isoString);
    const options: Intl.DateTimeFormatOptions = {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    };
    return date.toLocaleString('en-US', options);
  }

  /**
   * Format ISO date to short format (e.g., "DEC 9")
   */
  private formatDate(isoString: string): string {
    const date = new Date(isoString);
    const month = date.toLocaleString('en-US', { month: 'short' }).toUpperCase();
    const day = date.getDate();
    return `${month} ${day}`;
  }
}
