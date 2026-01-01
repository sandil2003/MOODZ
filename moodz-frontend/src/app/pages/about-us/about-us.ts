import { Component, OnInit, signal, OnDestroy } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-about-us',
  imports: [RouterLink],
  templateUrl: './about-us.html',
  styleUrl: './about-us.css'
})
export class AboutUs implements OnInit, OnDestroy {
  typedText = signal<string>('');
  isTypingComplete = signal<boolean>(false);
  private fullText = 'Empowering Mental Wellness Through AI Innovation';
  private typingInterval: any;
  private currentIndex = 0;

  ngOnInit() {
    this.startTypingAnimation();
  }

  ngOnDestroy() {
    if (this.typingInterval) {
      clearInterval(this.typingInterval);
    }
  }

  private startTypingAnimation() {
    this.typingInterval = setInterval(() => {
      if (this.currentIndex < this.fullText.length) {
        this.typedText.set(this.fullText.substring(0, this.currentIndex + 1));
        this.currentIndex++;
      } else {
        clearInterval(this.typingInterval);
        this.isTypingComplete.set(true);
      }
    }, 50); // 50ms per character for smooth typing
  }
}
