import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { User } from 'src/app/interfaces/user';
import { UserApiService } from '../api/user-api.service';
import { ConvertJsonService } from '../common/convert-json.service';
import { BaseDataService } from './base-data.service';
import { RoleDataService } from './role-data.service';
import { RuleDataService } from './rule-data.service';

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
    this.getDependentResources();
  }

  async getDependentResources() {
    (await this.ruleDataService.list()).subscribe((rules) => {
      this.rules = rules;
    });
    (await this.roleDataService.list()).subscribe((roles) => {
      this.roles = roles;
    });
  }

  async get(
    id: number,
    force_refresh: boolean = false
  ): Promise<Observable<User>> {
    return (await super.get_base(
      id,
      this.convertJsonService.getUser,
      [this.roles, this.rules],
      force_refresh
    )) as Observable<User>;
  }

  async list(
    roles: Role[],
    rules: Rule[],
    force_refresh: boolean = false
  ): Promise<Observable<User[]>> {
    return (await super.list_base(
      this.convertJsonService.getUser,
      [roles, rules],
      force_refresh
    )) as Observable<User[]>;
  }

  async list_with_params(
    roles: Role[] = [],
    rules: Rule[] = [],
    request_params: any = {},
    save: boolean = true
  ): Promise<User[]> {
    return (await super.list_with_params_base(
      this.convertJsonService.getUser,
      [roles, rules],
      request_params,
      save
    )) as User[];
  }

  async org_list(
    organization_id: number,
    roles: Role[],
    rules: Rule[],
    force_refresh: boolean = false
  ): Promise<Observable<User[]>> {
    return (await super.org_list_base(
      organization_id,
      this.convertJsonService.getUser,
      [roles, rules],
      force_refresh
    )) as Observable<User[]>;
  }
}
