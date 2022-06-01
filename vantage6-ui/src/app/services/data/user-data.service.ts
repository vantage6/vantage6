import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { User } from 'src/app/interfaces/user';
import { Resource } from 'src/app/shared/types';
import { removeMatchedIdFromArray } from 'src/app/shared/utils';
import { ApiUserService } from '../api/api-user.service';
import { ConvertJsonService } from '../common/convert-json.service';
import { BaseDataService } from './base-data.service';

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
  ): Promise<Observable<User>> {
    return (await super.get_base(
      id,
      this.convertJsonService.getUser,
      [roles, rules],
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

  // TODO we may want to generalize this function in the base data service
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
        await this.apiService.getOrganizationUsers(
          organization_id,
          roles,
          rules
        );
    }
    return this.org_users_dict[organization_id];
  }

  add_to_org(user: User) {
    console.log(this.org_users_dict[user.organization_id]);
    const updated_list = [...this.org_users_dict[user.organization_id], user];
    console.log(updated_list);
    this.org_users_dict[user.organization_id] = updated_list;
  }

  remove_from_org(user: User) {
    this.org_users_dict[user.organization_id] = removeMatchedIdFromArray(
      this.org_users_dict[user.organization_id],
      user.id
    );
    console.log(this.resource_list.value);
  }
}
