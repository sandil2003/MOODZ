import { Injectable } from '@angular/core';

export interface MoodHistoryEntry {
    id: number;
    user_id: string;
    mood_score: number;
    sentiment_label: string | null;
    topics: string[];
    summary: string;
    session_id: string | null;
    created_at: string;
}

export interface UserFact {
    id: number;
    user_id: string;
    fact_text: string;
    category: string;
    source: string;
    created_at: string;
}

export interface MoodStats {
    total_entries: number;
    average_mood: number | null;
    highest_mood: number | null;
    lowest_mood: number | null;
    most_common_sentiment: string | null;
    days_analyzed: number;
    trend: 'improving' | 'declining' | 'stable';
}

@Injectable({
    providedIn: 'root'
})
export class MoodDataService {
    private readonly API_BASE_URL = 'http://localhost:8001';

    async getMoodHistory(
        userId: string,
        limit: number = 50,
        days?: number
    ): Promise<MoodHistoryEntry[]> {
        let url = `${this.API_BASE_URL}/api/mood-data/mood-history/${userId}?limit=${limit}`;
        if (days) {
            url += `&days=${days}`;
        }

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Failed to fetch mood history: ${response.status}`);
        }

        return await response.json();
    }

    async getUserFacts(
        userId: string,
        category?: string,
        limit: number = 100
    ): Promise<UserFact[]> {
        let url = `${this.API_BASE_URL}/api/mood-data/user-facts/${userId}?limit=${limit}`;
        if (category) {
            url += `&category=${category}`;
        }

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Failed to fetch user facts: ${response.status}`);
        }

        return await response.json();
    }

    async getMoodStats(userId: string, days: number = 30): Promise<MoodStats> {
        const url = `${this.API_BASE_URL}/api/mood-data/mood-stats/${userId}?days=${days}`;

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Failed to fetch mood stats: ${response.status}`);
        }

        return await response.json();
    }
}
