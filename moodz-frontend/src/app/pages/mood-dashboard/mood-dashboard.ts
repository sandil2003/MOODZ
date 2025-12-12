import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

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

export class MoodDashboard {
  // Average score data
  averageScore = signal<number>(5.0);
  maxScore = signal<number>(10);

  // Sentiment data
  sentiment = signal<SentimentData>({
    label: 'Mixed',
    badge: 'NEUTRAL',
    description: 'Balanced mix of anxiety and optimism detected in recent entries.'
  });

  // Insights data
  insights = signal<Insight[]>([
    {
      id: 1,
      text: 'You have a presentation tomorrow that you\'ve been working on for a week.',
      source: 'MOOD ENTRY',
      date: 'DEC 9'
    },
    {
      id: 2,
      text: 'Feeling drained after work seems to be a recurring pattern.',
      source: 'PATTERN ANALYSIS',
      date: ''
    },
    {
      id: 3,
      text: 'Connecting with friends boosts your optimism significantly.',
      source: 'MOOD ENTRY',
      date: 'DEC 7'
    }
  ]);

  // Mood timeline entries
  moodEntries = signal<MoodEntry[]>([
    {
      id: 1,
      title: 'Feeling Anxious',
      score: 3,
      maxScore: 10,
      timestamp: 'Dec 9, 09:30 AM',
      description: '"I\'m feeling really stressed about my presentation tomorrow. I\'ve been working on it all week but I\'m still worried."',
      type: 'anxious'
    },
    {
      id: 2,
      title: 'A Bit Down',
      score: 4,
      maxScore: 10,
      timestamp: 'Dec 8, 06:15 PM',
      description: '"Just finished a long day of work. Feeling a little drained and unmotivated for some reason."',
      type: 'down'
    },
    {
      id: 3,
      title: 'Feeling Positive',
      score: 8,
      maxScore: 10,
      timestamp: 'Dec 7, 11:30 AM',
      description: '"Had a great call with a friend and feeling much more optimistic about the week ahead."',
      type: 'positive'
    }
  ]);
}

