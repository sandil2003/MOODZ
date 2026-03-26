import { Component, signal, inject, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

interface Agent {
  id: string;
  name: string;
  subtitle: string;
  description: string;
  icon: string;
  color: string;
  glowColor: string;
  imageUrl: string;
  status: 'online' | 'ready';
  route: string;
}

export interface LlmProvider {
  id: string;
  name: string;
  description: string;
  icon: string;
  accentColor: string;
}

@Component({
  selector: 'app-new-home',
  imports: [CommonModule, FormsModule],
  templateUrl: './new-home.html',
  styleUrl: './new-home.css',
  host: {
    'class': 'block'
  }
})
export class NewHomeComponent {
  private router = inject(Router);

  // LLM Provider state
  llmProviders: LlmProvider[] = [
    {
      id: 'anthropic',
      name: 'Anthropic API',
      description: 'Claude models — advanced reasoning & safety',
      icon: 'psychology',
      accentColor: '#D97757'
    },
    {
      id: 'gemini',
      name: 'Gemini API',
      description: 'Google Gemini — multimodal intelligence',
      icon: 'auto_awesome',
      accentColor: '#4285F4'
    },
    {
      id: 'openai',
      name: 'OpenAI API',
      description: 'GPT models — versatile & powerful',
      icon: 'smart_toy',
      accentColor: '#10A37F'
    },
    {
      id: 'custom',
      name: 'Custom API',
      description: 'Use your own model endpoint',
      icon: 'tune',
      accentColor: '#8B5CF6'
    }
  ];

  selectedProvider = signal<LlmProvider>(this.llmProviders[1]); // default Gemini
  showProviderModal = signal(false);
  customApiUrl = signal('');

  toggleProviderModal(): void {
    this.showProviderModal.update(v => !v);
  }

  selectProvider(provider: LlmProvider): void {
    this.selectedProvider.set(provider);
    if (provider.id !== 'custom') {
      this.showProviderModal.set(false);
    }
  }

  confirmCustomProvider(): void {
    this.showProviderModal.set(false);
  }

  @HostListener('document:keydown.escape')
  onEscapeKey(): void {
    this.showProviderModal.set(false);
  }

  currentTime = signal('');
  greeting = signal('');

  agents = signal<Agent[]>([
    {
      id: 'mood',
      name: 'Mood Agent',
      subtitle: 'Emotional Intelligence',
      description: "Feeling overwhelmed? I'm here to provide empathy, track your mood patterns, and offer emotional support.",
      icon: 'mood',
      color: 'beige',
      glowColor: 'shadow-glow-beige',
      imageUrl: '/mood%20agent.548Z.png',
      status: 'online',
      route: '/mood-agent'
    },
    {
      id: 'journal',
      name: 'Journal Agent',
      subtitle: 'Reflective Analysis',
      description: "Let's organize your thoughts. I help with daily reflections, structuring ideas, and maintaining your personal log.",
      icon: 'edit_note',
      color: 'red',
      glowColor: 'shadow-glow-red',
      imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCCD1UdAWFuIiHYI2C8b9E3su3RjJvNTEkwK9h1hNeThwyD3m2XTjtsvZYnyNWRfmce4DhtES31Ijo8TjFuF8bhiBu4ZbnwAHTqqjk92ZpPGPwpG3I71JDBYRK_JJtm02JuH52OllNBUTYiRlDvXXzbqKatRHO3muJnB7pvNjvKSIkrhvaSBt-Hjq2LKAPcIdl-Y6xvlcBnhz5GPDLsBan2xPbkHgA0tlTO4Ayg5U48HKFX_UsqSq6KM-rs_KM32IadRoi78tmvkjnl',
      status: 'ready',
      route: '/journal'
    },
    {
      id: 'study',
      name: 'Study Agent',
      subtitle: 'Academic Assistant',
      description: 'Need to focus? I can assist with research, create custom learning plans, and analyze complex topics for you.',
      icon: 'school',
      color: 'green',
      glowColor: 'shadow-glow-green',
      imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAWM_fA9O3QSQPtpc4SCEC3IU2x-nRQc_08JyktOAjrDyd8IfwLQqMWriWF198nqVGAsozhWiJT1th3U53nEoo9mJsGL7UHwr670eFVLIQZecNffDdsvMaeL3NbvITmTzBS174bsHLw2awpuyCjtto0fRYws7eruhOR-Tj5Jq1-eifMe_UpKNFpTDWXJE-1TzAYz547D7ctEamKsFY5XHStQZnDoGv4pVJmt2CVBA6xSJ-41HoalBLdUcusTxdcZs5O2s7NEjOrvB5z',
      status: 'online',
      route: '/study'
    }
  ]);

  constructor() {
    this.updateTimeAndGreeting();
    // Update time every minute
    setInterval(() => this.updateTimeAndGreeting(), 60000);
  }

  private updateTimeAndGreeting(): void {
    const now = new Date();
    const hour = now.getHours();

    if (hour < 12) {
      this.greeting.set('Good morning');
    } else if (hour < 18) {
      this.greeting.set('Good afternoon');
    } else {
      this.greeting.set('Good evening');
    }
  }

  navigateToAgent(route: string): void {
    this.router.navigate([route]);
  }

  // Tooltip state for mood icon
  moodTooltipVisible = signal<boolean>(false);
  moodTooltipText = signal<string>('');
  private typingInterval: any = null;
  private readonly fullTooltipText = 'How are you feeling today?';

  showMoodTooltip(): void {
    // Clear any existing interval
    if (this.typingInterval) {
      clearInterval(this.typingInterval);
    }

    // Show tooltip
    this.moodTooltipVisible.set(true);
    this.moodTooltipText.set('');

    // Start typing animation
    let charIndex = 0;
    this.typingInterval = setInterval(() => {
      if (charIndex < this.fullTooltipText.length) {
        this.moodTooltipText.set(this.fullTooltipText.substring(0, charIndex + 1));
        charIndex++;
      } else {
        clearInterval(this.typingInterval);
      }
    }, 50); // 50ms per character
  }

  hideMoodTooltip(): void {
    // Clear typing interval
    if (this.typingInterval) {
      clearInterval(this.typingInterval);
    }

    // Hide tooltip
    this.moodTooltipVisible.set(false);
    this.moodTooltipText.set('');
  }

  getColorClasses(color: string): { [key: string]: string } {
    const colorMap: { [key: string]: { [key: string]: string } } = {
      beige: {
        bg: 'bg-amber-50',
        text: 'text-amber-700',
        hoverText: 'group-hover:text-amber-700',
        ring: 'hover:ring-amber-200'
      },
      purple: {
        bg: 'bg-purple-50',
        text: 'text-purple-600',
        hoverText: 'group-hover:text-purple-600',
        ring: 'hover:ring-purple-200'
      },
      red: {
        bg: 'bg-red-50',
        text: 'text-red-600',
        hoverText: 'group-hover:text-red-600',
        ring: 'hover:ring-red-200'
      },
      green: {
        bg: 'bg-green-50',
        text: 'text-green-600',
        hoverText: 'group-hover:text-green-600',
        ring: 'hover:ring-green-200'
      }
    };

    return colorMap[color] || colorMap['beige'];
  }
}
