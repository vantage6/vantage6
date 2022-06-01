import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { User } from 'src/app/interfaces/user';
import { ApiUserService } from '../api/api-user.service';
import { ConvertJsonService } from '../common/convert-json.service';
import { BaseDataService } from './base-data.service';
import { add_to_org, remove_from_org } from './utils';

@Injectable({
  providedIn: 'root',
})
export class UserDataService extends BaseDataService {
  org_users_dict: { [org_id: number]: User[] } = {};

  constructor(
    protected apiService: ApiUserService,
    protected convertJsonService: ConvertJsonService
  ) {
    super(apiService, convertJsonService);
  }

  async get(
    id: number,
    roles: Role[],
    rules: Rule[],
    force_refresh: boolean = false
  ): Promise<User> {
    return (await super.get_base(
      id,
      this.convertJsonService.getUser,
      [roles, rules],
      force_refresh
    )) as User;
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

  async org_list(
    organization_id: number,
    roles: Role[],
    rules: Rule[],
    force_refresh: boolean = false
  ): Promise<User[]> {
    if (
      force_refresh ||
      !(organization_id in this.org_users_dict) ||
      this.org_users_dict[organization_id].length === 0
    ) {
      this.org_users_dict[organization_id] =
        (await this.apiService.getResources(
          this.convertJsonService.getUser,
          [roles, rules],
          { organization_id: organization_id }
        )) as User[];
    }
    return this.org_users_dict[organization_id];
  }

  add(user: User) {
    super.add(user);
    add_to_org(user, this.org_users_dict);
  }

  remove(user: User) {
    super.remove(user);
    remove_from_org(user, this.org_users_dict);
  }
}
