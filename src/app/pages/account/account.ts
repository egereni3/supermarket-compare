import { Component } from '@angular/core';
import { NgForOf, NgIf, AsyncPipe, CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Basket, BasketItem } from '../../services/basket';
import { Observable } from 'rxjs';
import { Auth } from '../../auth/auth';

@Component({
  selector: 'app-account',
  standalone: true,
  imports: [NgForOf, NgIf, AsyncPipe, CommonModule, FormsModule],
  templateUrl: './account.html',
  styleUrls: ['./account.scss'],
})
export class Account {
  items$: Observable<BasketItem[]>;

  // profile form fields
  currentEmail = '';
  newEmail = '';
  emailPassword = '';
  emailError: string | null = null;
  emailMessage: string | null = null;
  showEmailForm = false;

  currentPasswordForChange = '';
  newPassword = '';
  confirmNewPassword = '';
  passError: string | null = null;
  passMessage: string | null = null;
  showPasswordForm = false;

  constructor(private basket: Basket, private auth: Auth) {
    this.items$ = this.basket.items$; // typed as Observable<BasketItem[]>
    const user = this.auth.getUser();
    this.currentEmail = user?.email ?? '';
  }

  remove(id: string): void {
    this.basket.remove(id);
  }

  clear(): void {
    this.basket.clear();
  }

  // Verify current password by attempting login, then update local email
  updateEmail(): void {
    this.emailError = null;
    this.emailMessage = null;
    if (!this.newEmail.trim() || !this.emailPassword.trim()) {
      this.emailError = 'New email and current password are required.';
      return;
    }
    // verify current password
    this.auth.login(this.currentEmail, this.emailPassword).subscribe({
      next: (resp) => {
        if (!resp.success) {
          this.emailError = resp.error ?? 'Current password incorrect.';
          return;
        }
        const userId = this.auth.getUser()?.id;
        if (!userId) {
          this.emailError = 'User not found locally.';
          return;
        }
        // call server to update email
        this.auth.updateUser(userId, { email: this.newEmail.trim() }).subscribe({
          next: (uResp: any) => {
            if (!uResp.success) {
              this.emailError = uResp.error ?? 'Update failed.';
              return;
            }
            // update local storage and UI
            this.auth.updateLocalEmail(this.newEmail.trim());
            this.currentEmail = this.newEmail.trim();
            this.newEmail = '';
            this.emailPassword = '';
            this.emailMessage = 'Email updated successfully.';
            this.showEmailForm = false;
          },
          error: (err: any) => {
            this.emailError = err?.error?.error ?? err?.message ?? 'Server error.';
          },
        });
      },
      error: (err) => {
        this.emailError = err?.error?.error ?? err?.message ?? 'Server error.';
      },
    });
  }

  // Verify current password then validate new password and show success message
  updatePassword(): void {
    this.passError = null;
    this.passMessage = null;
    if (!this.currentPasswordForChange.trim() || !this.newPassword.trim() || !this.confirmNewPassword.trim()) {
      this.passError = 'All password fields are required.';
      return;
    }
    if (this.newPassword !== this.confirmNewPassword) {
      this.passError = 'New passwords do not match.';
      return;
    }
    if (this.newPassword.length < 6 || !/[A-Z]/.test(this.newPassword) || !/[0-9]/.test(this.newPassword)) {
      this.passError = 'Password must be at least 6 characters, contain an uppercase letter and a number.';
      return;
    }

    // verify current password
    this.auth.login(this.currentEmail, this.currentPasswordForChange).subscribe({
      next: (resp) => {
        if (!resp.success) {
          this.passError = resp.error ?? 'Current password incorrect.';
          return;
        }
        const userId = this.auth.getUser()?.id;
        if (!userId) {
          this.passError = 'User not found locally.';
          return;
        }
        // call server to update password
        this.auth.updateUser(userId, { password: this.newPassword }).subscribe({
          next: (uResp: any) => {
            if (!uResp.success) {
              this.passError = uResp.error ?? 'Password update failed.';
              return;
            }
            this.currentPasswordForChange = '';
            this.newPassword = '';
            this.confirmNewPassword = '';
            this.passMessage = 'Password updated successfully.';
            this.showPasswordForm = false;
          },
          error: (err: any) => {
            this.passError = err?.error?.error ?? err?.message ?? 'Server error.';
          },
        });
      },
      error: (err) => {
        this.passError = err?.error?.error ?? err?.message ?? 'Server error.';
      },
    });
  }
}