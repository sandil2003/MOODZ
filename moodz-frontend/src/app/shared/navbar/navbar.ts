import { Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-navbar',
  imports: [RouterLink, CommonModule],
  templateUrl: './navbar.html',
  styleUrl: './navbar.css',
})
export class Navbar {
  tooltipVisible = signal<boolean[]>([false, false, false]);
  tooltipText = signal<string[]>(['', '', '']);

  private fullTexts = ['Mood Dashboard', 'Toggle Dark Mode', 'Home'];
  private typingIntervals: any[] = [];

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
}
