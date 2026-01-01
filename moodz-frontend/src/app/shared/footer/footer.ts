import { Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-footer',
  imports: [RouterLink],
  templateUrl: './footer.html',
  styleUrl: './footer.css',
})
export class Footer {
  currentYear = new Date().getFullYear();

  // Dropdown states for mobile
  agentsDropdownOpen = signal(false);
  featuresDropdownOpen = signal(false);

  toggleAgentsDropdown() {
    this.agentsDropdownOpen.set(!this.agentsDropdownOpen());
  }

  toggleFeaturesDropdown() {
    this.featuresDropdownOpen.set(!this.featuresDropdownOpen());
  }
}
