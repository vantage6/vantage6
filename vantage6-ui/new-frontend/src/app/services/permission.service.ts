import { Injectable } from '@angular/core';
import { OperationType, ResourceType, Rule, ScopeType } from '../models/api/rule.model';
import { Pagination } from '../models/api/pagination.model';
import { Collaboration } from '../models/api/collaboration.model';
import { BaseUser } from '../models/api/user.model';
import { ApiService } from './api.service';
import { USER_ID } from '../models/constants/sessionStorage';

@Injectable({
  providedIn: 'root'
})
export class PermissionService {
  activeRules: Rule[] | null = null;
  activeUser: BaseUser | null = null;

  constructor(private apiService: ApiService) {}

  async initData() {
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

  isAllowedForOrg(resource: ResourceType, operation: OperationType, orgId: number | null) {
    if (!orgId || !this.activeUser) return false;
    if (
      this.isAllowed(ScopeType.GLOBAL, resource, operation) ||
      (orgId === this.activeUser.organization.id && this.isAllowed(ScopeType.ORGANIZATION, resource, operation))
    ) {
      return true;
    } else if (this.activeUser.permissions) {
      let orgs_in_user_collabs = this.activeUser.permissions.orgs_in_collabs;
      return orgId in orgs_in_user_collabs && this.isAllowed(ScopeType.COLLABORATION, resource, operation);
    } else {
      return false;
    }
  }

  isAllowedForCollab(resource: ResourceType, operation: OperationType, collab: Collaboration | null) {
    if (!collab || !this.activeUser) return false;
    let collab_org_ids = collab.organizations.map((org) => org.id);
    return (
      this.isAllowed(ScopeType.GLOBAL, resource, operation) ||
      (this.activeUser.organization.id in collab_org_ids && this.isAllowed(ScopeType.COLLABORATION, resource, operation))
    );
  }

  isAllowedWithMinScope(minScope: ScopeType, resource: ResourceType, operation: OperationType): boolean {
    // determine which scopes are at least minimum scope in hierarchy
    let scopes: ScopeType[] = [ScopeType.GLOBAL];
    if (minScope != ScopeType.GLOBAL) scopes.push(ScopeType.COLLABORATION);
    if (minScope != ScopeType.COLLABORATION) scopes.push(ScopeType.ORGANIZATION);
    if (minScope != ScopeType.ORGANIZATION) scopes.push(ScopeType.OWN);

    // check if user has at least one of the scopes
    return scopes.some((s) => this.isAllowed(s, resource, operation));
  }

  getActiveOrganizationID(): number | undefined {
    return this.activeUser?.organization.id;
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
