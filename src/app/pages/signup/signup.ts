import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Auth } from '../../auth/auth';
import { finalize, switchMap } from 'rxjs/operators';

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
    this.cdr.detectChanges();

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
      .register(this.email.trim(), this.password)
      .pipe(
        switchMap((resp: any) => {
          const body = resp?.body ?? resp;

          if (!body?.success) {
            throw new Error(body?.error || 'Registration failed.');
          }

          // Auto-login after successful registration
          return this.auth.login(this.email.trim(), this.password);
        }),
        finalize(() => {
          this.loading = false;
          this.cdr.detectChanges();
        })
      )
      .subscribe({
        next: () => {
          this.router.navigate(['/account']);
        },
        error: (err: any) => {
          this.error =
            err?.message ||
            err?.error?.error ||
            err?.error?.message ||
            'Registration failed. Please try again.';
          this.cdr.detectChanges(); 
        },
      });
  }
}