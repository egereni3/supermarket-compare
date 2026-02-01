import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Search } from '../../services/search';
import { Auth } from '../../auth/auth';
import { NgIf } from '@angular/common';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [FormsModule, NgIf],
  templateUrl: './home.html',
  styleUrl: './home.scss',
})
export class Home {
  query = '';
  loading = false;
  error: string | null = null;

  constructor(
    private search: Search,
    private router: Router,
    private auth: Auth,    
  ) {}

  get isLoggedIn(): boolean {
    return this.auth.isLoggedIn();
  }

  onSearch(): void {
    this.error = null;
    const trimmed = this.query.trim();
    if (!trimmed) {
      this.error = 'Please enter a query.';
      return;
    }

    this.loading = true;
    this.search.search(trimmed).subscribe({
      next: () => {
        this.loading = false;
        this.router.navigate(['/results'], { queryParams: { q: trimmed } });
      },
      error: () => {
        this.loading = false;
        this.error = 'Search failed. Please try again.';
      },
    });
  }
}