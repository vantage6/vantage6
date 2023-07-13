import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { User } from 'src/app/interfaces/user';
import { Resource } from 'src/app/shared/types';
import { UserApiService } from '../api/user-api.service';
import { ConvertJsonService } from '../common/convert-json.service';
import { BaseDataService } from './base-data.service';
import { RoleDataService } from './role-data.service';
import { RuleDataService } from './rule-data.service';
import {
  Pagination,
  allPages,
  defaultFirstPage,
} from 'src/app/interfaces/utils';
import { getIdsFromArray, removeMatchedIdsFromArray } from 'src/app/shared/utils';

/**
 * Service for retrieving and updating user data.
 */
@Injectable({
  providedIn: 'root',
})
export class UserDataService extends BaseDataService {
  rules: Rule[] = [];
  roles: Role[] = [];

  constructor(
    protected apiService: UserApiService,
    protected convertJsonService: ConvertJsonService,
    private ruleDataService: RuleDataService,
    private roleDataService: RoleDataService
  ) {
    super(apiService, convertJsonService);
  }

  /**
   * Update the cache for the given resources.
   *
   * This function is an override of the base class function.
   *
   * @param resources The resources to update the cache for.
   */
  updateObsById(resources: User[]): void {
    for (let res of resources) {
      if (res.id in this.resources_by_id) {
        let cur_val = this.resources_by_id[res.id].value as User;
        if (cur_val.rules.length > 0 && res.rules.length === 0) {
          res.rules = cur_val.rules;
        }
        if (cur_val.roles.length > 0 && res.roles.length === 0) {
          res.roles = cur_val.roles;
        }
        this.resources_by_id[res.id].next(res);
      } else {
        this.resources_by_id[res.id] = new BehaviorSubject<Resource | null>(
          res
        );
      }
    }
  }

  /**
   * Get the rules and roles, which are required to get users. This function
   * should be called before getting the users.
   *
   * This is an override of the base class function.
   *
   * @returns An array of rules and roles, which are required to get users.
   */
  async getDependentResources(): Promise<Resource[][]> {
    // TODO is this required? It seems more data may be collected than is needed
    (await this.ruleDataService.list(allPages())).subscribe((rules) => {
      this.rules = rules;
    });
    (await this.roleDataService.list(allPages())).subscribe((roles) => {
      this.roles = roles;
    });
    return [this.roles, this.rules];
  }

  /**
   * Get a user by id. If the user is not in the cache, it will be requested
   * from the vantage6 server.
   *
   * @param id The id of the user to get.
   * @param include_links Whether to include the rules and roles associated
   * with the user.
   * @param only_extra_rules Whether to only include rules that are not
   * already included in the roles.
   * @param force_refresh Whether to force a refresh of the cache.
   * @returns An observable of the user.
   */
  async get(
    id: number,
    include_links: boolean = false,
    only_extra_rules: boolean = false,
    force_refresh: boolean = false
  ): Promise<Observable<User>> {
    let user = await super.get_base(
      id,
      this.convertJsonService.getUser,
      force_refresh
    ) as BehaviorSubject<User>;
    if (include_links) {
      // for single resource, include the internal resources
      let user_value = user.value;
      // request the rules for the current user
      (await this.ruleDataService.list_with_params(
        allPages(),
        { user_id: user_value.id }
      )).subscribe((rules) => {
        user_value.rules = rules;
      });
      // add roles to the user
      (await this.roleDataService.list_with_params(
        allPages(),
        { user_id: user_value.id },
        true
      )).subscribe((roles) => {
        user_value.roles = roles;
      });
      if (only_extra_rules) {
        // remove rules that are already included in the roles
        for (let role of user_value.roles) {
          user_value.rules = removeMatchedIdsFromArray(
            user_value.rules, getIdsFromArray(role.rules)
          );
        }
      }
      user.next(user_value);
    }
    return user.asObservable();
  }

  /**
   * Get all users. If the users are not in the cache, they will be requested
   * from the vantage6 server.
   *
   * @param pagination The pagination parameters to use.
   * @param force_refresh Whether to force a refresh of the cache.
   * @returns An observable of the users.
   */
  async list(
    pagination: Pagination = defaultFirstPage(),
    force_refresh: boolean = false
  ): Promise<Observable<User[]>> {
    return (await super.list_base(
      this.convertJsonService.getUser,
      pagination,
      force_refresh
    )).asObservable() as Observable<User[]>;
  }

  /**
   * Get users with the given parameters. If the users are not in the cache,
   * they will be requested from the vantage6 server.
   *
   * @param request_params The parameters to use in the request.
   * @param save Whether to save the users to the cache.
   * @param pagination The pagination parameters to use.
   * @returns An observable of the users.
   */
  async list_with_params(
    request_params: any = {},
    save: boolean = true,
    pagination: Pagination = allPages()
  ): Promise<Observable<User[]>> {
    return (await super.list_with_params_base(
      this.convertJsonService.getUser,
      request_params,
      pagination,
      save
    )).asObservable() as Observable<User[]>;
  }

  /**
   * Get all users for an organization. If the users are not in the cache,
   * they will be requested from the vantage6 server.
   *
   * @param organization_id The id of the organization to get the users for.
   * @param force_refresh Whether to force a refresh of the cache.
   * @param pagination The pagination parameters to use.
   * @returns An observable of the users.
   */
  async org_list(
    organization_id: number,
    force_refresh: boolean = false,
    pagination: Pagination = allPages()
  ): Promise<Observable<User[]>> {
    return (await super.org_list_base(
      organization_id,
      this.convertJsonService.getUser,
      pagination,
      force_refresh
    )).asObservable() as Observable<User[]>;
  }

  /**
   * Save a user to the cache.
   *
   * @param user The user to save.
   */
  save(user: User): void {
    // remove organization - these should be set within components where
    // needed. Delete them here to prevent endless loop of updates
    if (user.organization) user.organization = undefined;
    super.save(user);
  }
}
