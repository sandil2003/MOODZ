import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  selector: 'app-home',
  imports: [],
  templateUrl: './home.html',
  styleUrl: './home.css',
  host: {
    '(document:mousemove)': 'onMouseMove($event)',
    '(document:mouseup)': 'onMouseUp()'
  }
})
export class Home {
  private router = inject(Router);

  private isDragging = false;
  private currentShapeIndex: number | null = null;
  private offsetX = 0;
  private offsetY = 0;

  activateAgent() {
    this.router.navigate(['/mood-agent']);
  }

  onMouseDown(event: MouseEvent, shapeIndex: number) {
    event.preventDefault();
    this.isDragging = true;
    this.currentShapeIndex = shapeIndex;

    const target = event.target as HTMLElement;
    const rect = target.getBoundingClientRect();

    this.offsetX = event.clientX - rect.left;
    this.offsetY = event.clientY - rect.top;

    target.style.cursor = 'grabbing';
  }

  onMouseMove(event: MouseEvent) {
    if (!this.isDragging || this.currentShapeIndex === null) return;

    const shapes = document.querySelectorAll('.shape');
    const shape = shapes[this.currentShapeIndex] as HTMLElement;

    if (shape) {
      const container = shape.parentElement;
      if (!container) return;

      const containerRect = container.getBoundingClientRect();

      let newLeft = event.clientX - containerRect.left - this.offsetX;
      let newTop = event.clientY - containerRect.top - this.offsetY;

      // Keep shapes within bounds
      const shapeRect = shape.getBoundingClientRect();
      newLeft = Math.max(0, Math.min(newLeft, containerRect.width - shapeRect.width));
      newTop = Math.max(0, Math.min(newTop, containerRect.height - shapeRect.height));

      shape.style.left = `${newLeft}px`;
      shape.style.top = `${newTop}px`;
      shape.style.right = 'auto';
      shape.style.bottom = 'auto';
    }
  }

  onMouseUp() {
    if (this.isDragging && this.currentShapeIndex !== null) {
      const shapes = document.querySelectorAll('.shape');
      const shape = shapes[this.currentShapeIndex] as HTMLElement;
      if (shape) {
        shape.style.cursor = 'grab';
      }
    }

    this.isDragging = false;
    this.currentShapeIndex = null;
  }
}
