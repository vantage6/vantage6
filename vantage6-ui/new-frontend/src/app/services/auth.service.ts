import { Injectable } from '@angular/core';
import { environment } from 'src/environments/environment.development';
import { LoginForm } from '../models/forms/login-form.model';
import { ApiService } from './api.service';

const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  constructor(private apiService: ApiService) {}

  async login(loginForm: LoginForm): Promise<void> {
    const data = {
      username: loginForm.username,
      password: loginForm.password
    };
    const result = await this.apiService.post(environment.api_url + '/token/user', data);
    this.setSession(result);
  }

  private setSession(result: any): void {
    this.clearSession();
    if (result.access_token) {
      sessionStorage.setItem(ACCESS_TOKEN_KEY, result.access_token);
    }
    if (result.refresh_token) {
      sessionStorage.setItem(REFRESH_TOKEN_KEY, result.refresh_token);
    }
  }

  private clearSession(): void {
    sessionStorage.clear();
  }
}
