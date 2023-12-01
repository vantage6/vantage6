import { Injectable } from '@angular/core';
import { OperationType, ResourceType, Rule, ScopeType } from '../models/api/rule.model';
import { Pagination } from '../models/api/pagination.model';
import { Collaboration } from '../models/api/collaboration.model';
import { BaseUser } from '../models/api/user.model';
import { ApiService } from './api.service';
import { USER_ID } from '../models/constants/sessionStorage';
import { BaseOrganization, Organization } from '../models/api/organization.model';

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

  constructor(private apiService: ApiService) {}

  async initData(): Promise<void> {
    if (this.activeRules === null) {
      // get user rules
      this.activeRules = await this.getUserRules();
    }
    if (this.activeUser === null) {
      // get user (knowing the user organization id is required to determine
      // what they are allowed to see for which organizations)
      this.activeUser = await this.getUser();
    }
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
      return orgId in orgsInUserCollabs && this.isAllowed(ScopeType.COLLABORATION, resource, operation);
    } else {
      return false;
    }
  }

  isAllowedForCollab(resource: ResourceType, operation: OperationType, collab: Collaboration | null): boolean {
    if (!collab || !this.activeUser) return false;
    const orgsInUserCollabs = collab.organizations.map((org) => org.id);
    return (
      this.isAllowed(ScopeType.GLOBAL, resource, operation) ||
      (this.activeUser.organization.id in orgsInUserCollabs && this.isAllowed(ScopeType.COLLABORATION, resource, operation))
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

  /**
   * Get all organizations that the user is allowed to perform 'operation' on 'resource'. E.g. all organizations for
   * which it is possible to create a role.
   * @param resource
   * @param operation
   * @returns
   */
  public getAllowedOrganizationsIds(resource: ResourceType, operation: OperationType): number[] {
    const ids = this.activeUser?.permissions?.orgs_in_collabs.filter((orgId) => this.isAllowedForOrg(resource, operation, orgId));
    return ids ?? [];
  }

  private async getUserRules() {
    const userId = sessionStorage.getItem(USER_ID);
    const result = await this.apiService.getForApi<Pagination<Rule>>('/rule', {
      user_id: userId,
      no_pagination: 1
    });
    return result.data;
  }

  private async getUser() {
    const userId = sessionStorage.getItem(USER_ID);
    return await this.apiService.getForApi<BaseUser>(`/user/${userId}`, {
      include_permissions: true
    });
  }
}
