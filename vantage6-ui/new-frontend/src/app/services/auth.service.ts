import { Injectable } from '@angular/core';
import { LoginForm } from '../models/forms/login-form.model';
import { ApiService } from './api.service';
import { Login } from '../models/api/login.model';
import { OperationType, ResourceType, Rule, ScopeType } from '../models/api/rule.model';
import { Pagination } from '../models/api/pagination.model';
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY, USER_ID } from '../models/constants/sessionStorage';
import { BaseUser } from '../models/api/user.model';
import { routePaths } from '../routes';

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

    //TODO: Fully validate JTW token
    const isExpired = Date.now() >= JSON.parse(atob(token.split('.')[1])).exp * 1000;

    if (!isExpired && this.activeRules === null) {
      await this.getUserRules();
    }
    return !isExpired;
  }

  async getUser(): Promise<BaseUser> {
    const userId = sessionStorage.getItem(USER_ID);
    return await this.apiService.getForApi<BaseUser>(`/user/${userId}`);
  }

  hasResourceInScope(scope: ScopeType, resource: ResourceType): boolean {
    if (scope === ScopeType.ANY) {
      return !!this.activeRules?.some((rule) => rule.name.toLowerCase() === resource);
    }

    return !!this.activeRules?.some((rule) => rule.name.toLowerCase() === resource && rule.scope.toLowerCase() === scope);
  }

  isOperationAllowed(scope: ScopeType, resource: ResourceType, operation: OperationType): boolean {
    if (scope === ScopeType.ANY) {
      return !!this.activeRules?.some((rule) => rule.name.toLowerCase() === resource && rule.operation.toLowerCase() === operation);
    }

    return !!this.activeRules?.some(
      (rule) => rule.scope.toLowerCase() === scope && rule.name.toLowerCase() === resource && rule.operation.toLowerCase() === operation
    );
  }

  logout(): void {
    this.clearSession();
  }

  private async getUserRules() {
    const userId = sessionStorage.getItem(USER_ID);
    const result = await this.apiService.getForApi<Pagination<Rule>>('/rule', {
      user_id: userId,
      no_pagination: 1
    });
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
