import { Component, signal, inject, OnInit } from '@angular/core';
import { Router, RouterLink, NavigationEnd } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ThemeService } from '../../services/theme.service';
import { filter } from 'rxjs/operators';

@Component({
  selector: 'app-navbar',
  imports: [RouterLink, CommonModule],
  templateUrl: './navbar.html',
  styleUrl: './navbar.css',
})
export class Navbar implements OnInit {
  tooltipVisible = signal<boolean[]>([false, false, false]);
  tooltipText = signal<string[]>(['', '', '']);
  isOnMoodDashboard = signal<boolean>(false);
  isOnHomePage = signal<boolean>(false);
  isOnMoodAgent = signal<boolean>(false);

  private fullTexts = ['Mood Dashboard', 'Toggle Dark Mode', 'Home'];
  private typingIntervals: any[] = [];
  private router = inject(Router);

  constructor(public themeService: ThemeService) { }

  ngOnInit() {
    // Check initial route
    this.checkRoute(this.router.url);

    // Listen to route changes
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe((event: any) => {
      this.checkRoute(event.urlAfterRedirects);
    });
  }

  private checkRoute(url: string) {
    this.isOnMoodDashboard.set(url.includes('/mood-dashboard') || url.includes('/mood-history'));
    this.isOnHomePage.set(url === '/' || url === '');
    this.isOnMoodAgent.set(url.includes('/mood-agent'));
  }

  showTooltip(index: number): void {
    // Clear any existing interval
    if (this.typingIntervals[index]) {
      clearInterval(this.typingIntervals[index]);
    }

    // Show tooltip
    const visible = [...this.tooltipVisible()];
    visible[index] = true;
    this.tooltipVisible.set(visible);

    // Reset text
    const texts = [...this.tooltipText()];
    texts[index] = '';
    this.tooltipText.set(texts);

    // Start typing animation
    let charIndex = 0;
    const fullText = this.fullTexts[index];

    this.typingIntervals[index] = setInterval(() => {
      if (charIndex < fullText.length) {
        const texts = [...this.tooltipText()];
        texts[index] = fullText.substring(0, charIndex + 1);
        this.tooltipText.set(texts);
        charIndex++;
      } else {
        clearInterval(this.typingIntervals[index]);
      }
    }, 50); // 50ms per character for smooth typing effect
  }

  hideTooltip(index: number): void {
    // Clear typing interval
    if (this.typingIntervals[index]) {
      clearInterval(this.typingIntervals[index]);
    }

    // Hide tooltip
    const visible = [...this.tooltipVisible()];
    visible[index] = false;
    this.tooltipVisible.set(visible);

    // Reset text
    const texts = [...this.tooltipText()];
    texts[index] = '';
    this.tooltipText.set(texts);
  }

  toggleDarkMode(): void {
    this.themeService.toggleDarkMode();
  }
}
