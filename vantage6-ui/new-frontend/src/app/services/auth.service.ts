import { Injectable } from '@angular/core';
import { LoginForm } from '../models/forms/login-form.model';
import { ApiService } from './api.service';
import { Login } from '../models/api/login.model';
import { OperationType, ResourceType, Rule, ScopeType } from '../models/api/rule.model';
import { Pagination } from '../models/api/pagination.model';
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY, USER_ID } from '../models/constants/sessionStorage';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  activeRules: Rule[] | null = null;

  constructor(private apiService: ApiService) {}

  async login(loginForm: LoginForm): Promise<boolean> {
    const data = {
      username: loginForm.username,
      password: loginForm.password
    };
    const result = await this.apiService.postForApi<Login>('/token/user', data);
    this.setSession(result);
    return await this.isAuthenticated();
  }

  async isAuthenticated(): Promise<boolean> {
    const token = sessionStorage.getItem(ACCESS_TOKEN_KEY);

    if (!token) {
      return false;
    }

    const isExpired = Date.now() >= JSON.parse(atob(token.split('.')[1])).exp * 1000;

    if (!isExpired && this.activeRules === null) {
      await this.getUserRules();
    }
    return !isExpired;
  }

  hasResourceInScope(resource: ResourceType, scope: ScopeType): boolean {
    return !!this.activeRules?.some((rule) => rule.name.toLowerCase() === resource && rule.scope.toLowerCase() === scope);
  }

  isOperationAllowed(resource: ResourceType, scope: ScopeType, operation: OperationType): boolean {
    return !!this.activeRules?.some(
      (rule) => rule.name.toLowerCase() === resource && rule.scope.toLowerCase() === scope && rule.operation.toLowerCase() === operation
    );
  }

  private async getUserRules() {
    const userId = sessionStorage.getItem(USER_ID);
    const result = await this.apiService.getForApi<Pagination<Rule>>(`/rule?user_id=${userId}`);
    this.activeRules = result.data;
  }

  private setSession(result: Login): void {
    this.clearSession();

    if (!result.access_token) return;

    sessionStorage.setItem(ACCESS_TOKEN_KEY, result.access_token);
    sessionStorage.setItem(REFRESH_TOKEN_KEY, result.refresh_token);
    sessionStorage.setItem(USER_ID, result.user_url.split('/').pop() || '');
  }

  private clearSession(): void {
    sessionStorage.clear();
  }
}
