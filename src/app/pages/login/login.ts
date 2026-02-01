import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Auth } from '../../auth/auth';

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
  responseMessage: string | null = null;
  loading = false;

  constructor(private auth: Auth, private router: Router) {}

  isValidEmail(email: string): boolean {
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$/;
    return emailRegex.test(email);
  }

  onSubmit(): void {
    this.error = null;
    this.responseMessage = null;

    if (!this.email.trim() || !this.password.trim()) {
      this.error = 'Email and password are required.';
      return;
    }

    if (!this.isValidEmail(this.email)) {
      this.error = 'Please enter a valid email address.';
      return;
    }

    if (this.password.length < 6) {
      this.error = 'Password must be at least 6 characters long, contain an uppercase letter, and a number.';
      return;
    }
    if (!/[A-Z]/.test(this.password)) {
      this.error = 'Password must contain at least one uppercase letter.';
      return;
    }
    if (!/[0-9]/.test(this.password)) {
      this.error = 'Password must contain at least one number.';
      return;
    }

    this.loading = true;
    this.auth.login(this.email.trim(), this.password).subscribe({
      next: (resp) => {
        this.loading = false;
        if (!resp.success) {
          this.error = resp.error ?? 'Login failed.';
          this.responseMessage = 'Login failed. Please check your credentials.';
          return;
        }
        this.responseMessage = 'Login successful!';
        this.router.navigate(['/account']);
      },
      error: (err: any) => {
        this.loading = false;
        const serverMsg =
          (err && (err.error?.error || err.error?.message || err.message)) ??
          'Server error. Please try again.';
        this.error = serverMsg;
        this.responseMessage = serverMsg;
      },
    });
  }
}