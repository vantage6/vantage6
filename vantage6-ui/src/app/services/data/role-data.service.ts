import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { RoleApiService } from 'src/app/services/api/role-api.service';
import { ConvertJsonService } from 'src/app/services/common/convert-json.service';
import { BaseDataService } from 'src/app/services/data/base-data.service';
import { Resource } from 'src/app/shared/types';
import { RuleDataService } from './rule-data.service';
import {
  Pagination,
  allPages,
  defaultFirstPage,
} from 'src/app/interfaces/utils';

/**
 * Service for retrieving and updating role data.
 */
@Injectable({
  providedIn: 'root',
})
export class RoleDataService extends BaseDataService {
  rules: Rule[] = [];

  constructor(
    protected apiService: RoleApiService,
    protected convertJsonService: ConvertJsonService,
    private ruleDataService: RuleDataService
  ) {
    super(apiService, convertJsonService);
  }

  /**
   * Get the rules, which are required to get roles. This function should be
   * called before getting the roles.
   *
   * This is an override of the base class function.
   *
   * @returns An array of rules, which are required to get roles.
   */
  async getDependentResources(): Promise<Resource[][]> {
    // TODO is this required? It seems to require more data to be collected
    // than is needed
    (await this.ruleDataService.list(allPages())).subscribe((rules) => {
      this.rules = rules;
      // TODO when rules change, update roles as well
    });
    return [this.rules];
  }

  /**
   * Get a role by id. If the role is not in the cache, it will be requested
   * from the vantage6 server.
   *
   * @param id The id of the role to get.
   * @param include_links Whether to include the rules associated with the
   * role.
   * @param force_refresh Whether to force a refresh of the cache.
   * @returns An observable of the role.
   */
  async get(
    id: number,
    include_links: boolean = false,
    force_refresh: boolean = false
  ): Promise<Observable<Role>> {
    let role = await super.get_base(
        id, this.convertJsonService.getRole, force_refresh
    );
    if (include_links) {
      let role_value = (role as BehaviorSubject<Role>).value;
      role_value = await this.addRulesToRole(role_value);
      role.next(role_value);
    }
    return role.asObservable() as Observable<Role>;
  }

  /**
   * Get all roles. If the roles are not in the cache, they will be requested
   * from the vantage6 server.
   *
   * @param pagination The pagination parameters to use.
   * @param include_rules Whether to include the rules associated with the
   * roles.
   * @param force_refresh Whether to force a refresh of the cache.
   * @returns An observable of the roles.
   */
  async list(
    pagination: Pagination = defaultFirstPage(),
    include_rules: boolean = false,
    force_refresh: boolean = false,
  ): Promise<Observable<Role[]>> {
    let roles = (await super.list_base(
      this.convertJsonService.getRole,
      pagination,
      force_refresh
    ));
    if (include_rules) {
      let roles_value = (roles as BehaviorSubject<Role[]>).value;
      roles_value = await this.addRulesToRoles(roles_value);
      roles.next(roles_value);
    }
    return roles.asObservable() as Observable<Role[]>;
  }

  /**
   * Get all roles with the given parameters. If the roles are not in the
   * cache, they will be requested from the vantage6 server.
   *
   * @param pagination The pagination parameters to use.
   * @param request_params The parameters to use in the request.
   * @param include_rules Whether to include the rules associated with the
   * roles.
   * @returns An observable of the roles.
   */
  async list_with_params(
    pagination: Pagination = allPages(),
    request_params: any = {},
    include_rules: boolean = false
  ): Promise<Observable<Role[]>> {
    let roles = (await super.list_with_params_base(
      this.convertJsonService.getRole,
      request_params,
      pagination
    )) as BehaviorSubject<Role[]>;
    if (include_rules) {
      let roles_value = (roles as BehaviorSubject<Role[]>).value;
      roles_value = await this.addRulesToRoles(roles_value);
      roles.next(roles_value);
    }
    return roles.asObservable() as Observable<Role[]>;
  }

  /**
   * Get all roles for an organization. If the roles are not in the cache,
   * they will be requested from the vantage6 server.
   *
   * @param organization_id The id of the organization to get the roles for.
   * @param include_rules Whether to include the rules associated with the
   * roles.
   * @param force_refresh Whether to force a refresh of the cache.
   * @param pagination The pagination parameters to use.
   * @returns An observable of the organization's roles.
   */
  async org_list(
    organization_id: number,
    include_rules: boolean = false,
    force_refresh: boolean = false,
    pagination: Pagination = allPages()
  ): Promise<Observable<Role[]>> {
    let roles = (await super.org_list_base(
      organization_id,
      this.convertJsonService.getRole,
      pagination,
      force_refresh,
      { include_root: true }
    ))
    let roles_value = (roles as BehaviorSubject<Role[]>).value;
    roles_value = this.remove_non_user_roles(roles_value);
    if (include_rules){
      roles_value = await this.addRulesToRoles(roles_value);
    }
    roles.next(roles_value);

    return roles.asObservable() as Observable<Role[]>;
  }

  /**
   * Remove roles that cannot be assigned to users.
   *
   * @param roles The roles to filter.
   * @returns The filtered roles.
   */
  private remove_non_user_roles(roles: Role[]): Role[] {
    // remove container and node roles as these are not relevant to the users
    for (let role_name of ['container', 'node']) {
      roles = roles.filter(function (role: any) {
        return role.name !== role_name;
      });
    }
    return roles;
  }

  /**
   * Check whether a role is one of the vantage6 default roles.
   *
   * @param role The role to check.
   * @returns Whether the role is a default role or not.
   */
  isDefaultRole(role: Role): boolean {
    return role.organization_id === null;
  }

  /**
   * Add the rules to a list of roles.
   *
   * @param roles The roles to add the rules to.
   * @returns The roles with the rules added.
   */
  private async addRulesToRoles(roles: Role[]): Promise<Role[]> {
    for (let role of roles) {
      role = await this.addRulesToRole(role);
    }
    return roles;
  }

  /**
   * Add the rules to a role.
   *
   * @param role The role to add the rules to.
   * @returns The role with the rules added.
   */
  private async addRulesToRole(role: Role): Promise<Role> {
    (await this.ruleDataService.list_with_params(
      allPages(),
      { role_id: role.id }
    )).subscribe((rules) => {
      role.rules = rules;
    });
    return role;
  }
}
