import { Injectable } from '@angular/core';
import { OperationType, ResourceType, Rule, ScopeType } from 'src/app/models/api/rule.model';
import { Pagination } from 'src/app/models/api/pagination.model';
import { Collaboration } from 'src/app/models/api/collaboration.model';
import { BaseUser } from 'src/app/models/api/user.model';
import { ApiService } from './api.service';
import { BehaviorSubject, Observable } from 'rxjs';
import { RuleService } from './rule.service';
import { AuthService } from './auth.service';

const requiredScopeLevel: Record<ScopeType, ScopeType[]> = {
  [ScopeType.ANY]: [ScopeType.OWN, ScopeType.ORGANIZATION, ScopeType.COLLABORATION, ScopeType.GLOBAL],
  [ScopeType.OWN]: [ScopeType.OWN, ScopeType.ORGANIZATION, ScopeType.COLLABORATION, ScopeType.GLOBAL],
  [ScopeType.ORGANIZATION]: [ScopeType.ORGANIZATION, ScopeType.COLLABORATION, ScopeType.GLOBAL],
  [ScopeType.COLLABORATION]: [ScopeType.COLLABORATION, ScopeType.GLOBAL],
  [ScopeType.GLOBAL]: [ScopeType.GLOBAL]
};

@Injectable({
  providedIn: 'root'
})
export class PermissionService {
  activeRules: Rule[] | null = null;
  activeUser: BaseUser | null = null;
  initialized$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);

  constructor(
    private apiService: ApiService,
    private rulesService: RuleService,
    private authService: AuthService
  ) {
    this.rulesService.getRules();
    this.authService.authenticatedObservable().subscribe((loggedIn: boolean) => {
      if (loggedIn) this.initData();
    });
  }

  async initData(): Promise<void> {
    if (this.activeRules === null) {
      // get user rules
      this.activeRules = await this.getUserRules();
    }
    if (this.activeUser === null) {
      // get user (knowing the user organization id is required to determine
      // what they are allowed to see for which organizations)
      this.activeUser = await this.getUser();
      this.initialized$.next(true);
    }
  }

  isInitialized(): Observable<boolean> {
    return this.initialized$.asObservable();
  }

  async clear(): Promise<void> {
    this.activeRules = null;
    this.activeUser = null;
  }

  isAllowed(scope: ScopeType, resource: ResourceType, operation: OperationType): boolean {
    if (scope === ScopeType.ANY) {
      return !!this.activeRules?.some((rule) => rule.name.toLowerCase() === resource && rule.operation.toLowerCase() === operation);
    }

    return !!this.activeRules?.some(
      (rule) => rule.scope.toLowerCase() === scope && rule.name.toLowerCase() === resource && rule.operation.toLowerCase() === operation
    );
  }

  isAllowedForOrg(resource: ResourceType, operation: OperationType, orgId: number | null): boolean {
    if (!orgId || !this.activeUser) return false;
    if (
      this.isAllowed(ScopeType.GLOBAL, resource, operation) ||
      (orgId === this.activeUser.organization.id && this.isAllowed(ScopeType.ORGANIZATION, resource, operation))
    ) {
      return true;
    } else if (this.activeUser.permissions) {
      const orgsInUserCollabs = this.activeUser.permissions.orgs_in_collabs;
      return orgsInUserCollabs.includes(orgId) && this.isAllowed(ScopeType.COLLABORATION, resource, operation);
    } else {
      return false;
    }
  }

  isAllowedForCollab(resource: ResourceType, operation: OperationType, collab: Collaboration | null): boolean {
    if (!collab || !this.activeUser) return false;
    const orgsInUserCollabs = collab.organizations.map((org) => org.id);
    return (
      this.isAllowed(ScopeType.GLOBAL, resource, operation) ||
      (orgsInUserCollabs.includes(this.activeUser.organization.id) && this.isAllowed(ScopeType.COLLABORATION, resource, operation))
    );
  }

  isAllowedWithMinScope(minScope: ScopeType, resource: ResourceType, operation: OperationType): boolean {
    // determine which scopes are at least minimum scope in hierarchy
    const scopes: ScopeType[] = [ScopeType.GLOBAL];
    if (minScope !== ScopeType.GLOBAL) scopes.push(ScopeType.COLLABORATION);
    if (minScope !== ScopeType.COLLABORATION) scopes.push(ScopeType.ORGANIZATION);
    if (minScope !== ScopeType.ORGANIZATION) scopes.push(ScopeType.OWN);

    // check if user has at least one of the scopes
    return scopes.some((s) => this.isAllowed(s, resource, operation));
  }

  isAllowedToAssignRuleToRole(scope: ScopeType, resource: ResourceType, operation: OperationType): boolean {
    const scopes: ScopeType[] = requiredScopeLevel[scope];

    // check if user has at least one of the scopes
    return scopes.some((s) => this.isAllowed(s, resource, operation));
  }

  getActiveOrganizationID(): number | undefined {
    return this.activeUser?.organization.id;
  }

  private async getUserRules() {
    const result = await this.apiService.getForApi<Pagination<Rule>>('/rule', {
      current_user: 1,
      no_pagination: 1
    });
    return result.data;
  }

  private async getUser() {
    return await this.apiService.getForApi<BaseUser>(`/user/me`, {
      include_permissions: true
    });
  }
}
