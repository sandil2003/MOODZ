import { Component, OnInit, signal, inject } from '@angular/core';
import { Router, NavigationEnd, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { filter } from 'rxjs/operators';
import { ThemeService } from '../../services/theme.service';

@Component({
  selector: 'app-navbar',
  imports: [RouterLink, RouterLinkActive, CommonModule],
  templateUrl: './navbar.html',
  styleUrl: './navbar.css',
})
export class Navbar implements OnInit {
  tooltipVisible = signal<boolean[]>([false, false, false]);
  tooltipText = signal<string[]>(['', '', '']);
  isOnMoodDashboard = signal<boolean>(false);
  isOnHomePage = signal<boolean>(false);
  isOnMoodAgent = signal<boolean>(false);
  mobileMenuOpen = signal<boolean>(false);

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
    this.clearTypingInterval(index);
    this.tooltipVisible.set(this.tooltipVisible().map((_, i) => i === index));

    let currentText = '';
    let charIndex = 0;
    const fullText = this.fullTexts[index];

    this.typingIntervals[index] = setInterval(() => {
      if (charIndex < fullText.length) {
        currentText += fullText[charIndex];
        const newTexts = [...this.tooltipText()];
        newTexts[index] = currentText;
        this.tooltipText.set(newTexts);
        charIndex++;
      } else {
        this.clearTypingInterval(index);
      }
    }, 30);
  }

  hideTooltip(index: number): void {
    this.clearTypingInterval(index);
    const newVisible = [...this.tooltipVisible()];
    newVisible[index] = false;
    this.tooltipVisible.set(newVisible);

    const newTexts = [...this.tooltipText()];
    newTexts[index] = '';
    this.tooltipText.set(newTexts);
  }

  private clearTypingInterval(index: number): void {
    if (this.typingIntervals[index]) {
      clearInterval(this.typingIntervals[index]);
      this.typingIntervals[index] = null;
    }
  }

  toggleDarkMode(): void {
    this.themeService.toggleDarkMode();
  }

  toggleMobileMenu(): void {
    this.mobileMenuOpen.set(!this.mobileMenuOpen());
  }

  closeMobileMenu(): void {
    this.mobileMenuOpen.set(false);
  }
}
