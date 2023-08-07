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

  async login(loginForm: LoginForm): Promise<boolean> {
    const data = {
      username: loginForm.username,
      password: loginForm.password
    };
    const result = await this.apiService.post(environment.api_url + '/token/user', data);
    this.setSession(result);
    return this.isAuthenticated();
  }

  isAuthenticated(): boolean {
    //TODO: check if token is valid
    const hasAccessToken = !!sessionStorage.getItem(ACCESS_TOKEN_KEY);
    return hasAccessToken;
  }

  private setSession(result: any): void {
    this.clearSession();

    if (!result.access_token) return;

    sessionStorage.setItem(ACCESS_TOKEN_KEY, result.access_token);
    sessionStorage.setItem(REFRESH_TOKEN_KEY, result.refresh_token);
  }

  private clearSession(): void {
    sessionStorage.clear();
  }
}
