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

  updateObsById(resources: User[]) {
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
      user_value.rules = await this.ruleDataService.list_with_params(
        allPages(),
        { user_id: user_value.id }
      );
      // add roles to the user
      user_value.roles = await this.roleDataService.list_with_params(
        allPages(),
        { user_id: user_value.id },
        true
      );
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

  async list_with_params(
    request_params: any = {},
    save: boolean = true,
    pagination: Pagination = allPages()
  ): Promise<User[]> {
    return (await super.list_with_params_base(
      this.convertJsonService.getUser,
      request_params,
      pagination,
      save
    )) as User[];
  }

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

  save(user: User) {
    // remove organization - these should be set within components where
    // needed. Delete them here to prevent endless loop of updates
    if (user.organization) user.organization = undefined;
    super.save(user);
  }
}
