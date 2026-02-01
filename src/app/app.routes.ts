import { Routes } from '@angular/router';
import { Home } from './pages/home/home';
import { Login } from './pages/login/login';
import { Signup } from './pages/signup/signup';
import { Account } from './pages/account/account';
import { Results } from './pages/results/results';
import { authGuard } from './auth/auth-guard';

export const routes: Routes = [
  { path: '', component: Home },
  { path: 'login', component: Login },
  { path: 'signup', component: Signup },
  { path: 'results', component: Results },
  { path: 'account', component: Account, canActivate: [authGuard] },
  { path: '**', redirectTo: '' },
];