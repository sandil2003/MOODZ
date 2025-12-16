import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
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

@Component({
  selector: 'app-new-home',
  imports: [CommonModule],
  templateUrl: './new-home.html',
  styleUrl: './new-home.css',
  host: {
    'class': 'block'
  }
})
export class NewHomeComponent {
  private router = inject(Router);

  currentTime = signal('');
  greeting = signal('');

  agents = signal<Agent[]>([
    {
      id: 'mood',
      name: 'Mood Agent',
      subtitle: 'Emotional Intelligence',
      description: "Feeling overwhelmed? I'm here to provide empathy, track your mood patterns, and offer emotional support.",
      icon: 'mood',
      color: 'purple',
      glowColor: 'shadow-glow-purple',
      imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuB1BspbKW_TJBQ70dh2J1BZOqWeUbjkDsUoyZ1NucKN1PjOYSZsYVRSLJ2iPtns7V1Bt3ICh8eTqiZr_B3QVQdg-ydcbtPc4D1wtdh9oq7UnN9mXLSoBJWI6G0WokoX5UL1-RyCeOzncJQs9IxM96b9s-MOr33X4yd3oceBNmQO-W4ItYoR9rUMnuliU_n-5TtzzN9wqh-dB9UcDV3KIWaPqmGd7XgqGwCnGSm340m918QjDFPn6zZtK4B63ZS78t-iB4D4qH-FBJIQ',
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

  getColorClasses(color: string): { [key: string]: string } {
    const colorMap: { [key: string]: { [key: string]: string } } = {
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

    return colorMap[color] || colorMap['purple'];
  }
}
