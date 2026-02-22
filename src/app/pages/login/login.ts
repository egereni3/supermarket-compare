import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Auth } from '../../auth/auth';
import { finalize } from 'rxjs/operators';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.html',
  styleUrls: ['./login.scss'],
})
export class Login {
  email = '';
  password = '';
  error: string | null = null;
  loading = false;

  constructor(
    private auth: Auth,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  isValidEmail(email: string): boolean {
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$/;
    return emailRegex.test(email);
  }

  onSubmit(): void {
    this.error = null;

    if (!this.email.trim() || !this.password.trim()) {
      this.error = 'Email and password are required.';
      this.cdr.detectChanges();
      return;
    }

    if (!this.isValidEmail(this.email)) {
      this.error = 'Please enter a valid email address.';
      this.cdr.detectChanges();
      return;
    }

    if (
      this.password.length < 6 ||
      !/[A-Z]/.test(this.password) ||
      !/[0-9]/.test(this.password)
    ) {
      this.error =
        'Password must be at least 6 characters long and include an uppercase letter and a number.';
      this.cdr.detectChanges();
      return;
    }

    this.loading = true;
    this.cdr.detectChanges();

    this.auth
      .login(this.email.trim(), this.password)
      .pipe(
        finalize(() => {
          this.loading = false;
          this.cdr.detectChanges();
        })
      )
      .subscribe({
        next: (resp: any) => {
          const body = resp?.body ?? resp;

          if (!body?.success) {
            this.error = body?.error || 'Invalid email or password.';
            this.cdr.detectChanges(); 
            return;
          }

          this.router.navigate(['/account']);
        },

        error: (err: any) => {
          this.error =
            err?.error?.error ||
            err?.error?.message ||
            err?.message ||
            'Server error. Please try again.';
          this.cdr.detectChanges(); 
        },
      });
  }
}