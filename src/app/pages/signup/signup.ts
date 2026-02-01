import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Auth } from '../../auth/auth';

@Component({
  selector: 'app-signup',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './signup.html',
  styleUrls: ['./signup.scss'],
})
export class Signup {
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
    this.auth.register(this.email.trim(), this.password).subscribe({
      next: (resp) => {
        if (!resp.success) {
          this.loading = false;
          this.error = resp.error ?? 'Registration failed.';
          this.responseMessage = 'Registration failed. Please try again.';
          return;
        }

        // Auto-login after successful registration
        this.auth.login(this.email.trim(), this.password).subscribe({
          next: () => {
            this.loading = false;
            this.router.navigate(['/account']);
          },
          error: () => {
            this.loading = false;
            this.error = 'Registered but login failed. Please try logging in.';
            this.responseMessage = 'Registered but login failed. Please try logging in.';
          },
        });
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