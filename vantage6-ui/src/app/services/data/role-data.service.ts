import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { RoleApiService } from 'src/app/services/api/role-api.service';
import { ConvertJsonService } from 'src/app/services/common/convert-json.service';
import { BaseDataService } from 'src/app/services/data/base-data.service';

@Injectable({
  providedIn: 'root',
})
export class RoleDataService extends BaseDataService {
  constructor(
    protected apiService: RoleApiService,
    protected convertJsonService: ConvertJsonService
  ) {
    super(apiService, convertJsonService);
  }

  async get(
    id: number,
    rules: Rule[],
    force_refresh: boolean = false
  ): Promise<Role> {
    return (await super.get_base(
      id,
      this.convertJsonService.getRole,
      [rules],
      force_refresh
    )) as Role;
  }

  async list(
    rules: Rule[],
    force_refresh: boolean = false
  ): Promise<Observable<Role[]>> {
    return (await super.list_base(
      this.convertJsonService.getRole,
      [rules],
      force_refresh
    )) as Observable<Role[]>;
  }

  async list_with_params(
    rules: Rule[] = [],
    request_params: any = {}
  ): Promise<Role[]> {
    return (await super.list_with_params_base(
      this.convertJsonService.getRole,
      [rules],
      request_params
    )) as Role[];
  }

  async org_list(
    organization_id: number,
    rules: Rule[],
    force_refresh: boolean = false
  ): Promise<Role[]> {
    let roles: Role[] = [];
    if (force_refresh || !this.queried_org_ids.includes(organization_id)) {
      roles = (await this.apiService.getResources(
        this.convertJsonService.getRole,
        [rules],
        { organization_id: organization_id, include_root: true }
      )) as Role[];
      this.queried_org_ids.push(organization_id);
      this.saveMultiple(roles);
    } else {
      // this organization has been queried before: get matches from the saved
      // data
      for (let role of this.resource_list.value as Role[]) {
        if (
          role.organization_id === organization_id ||
          role.organization_id === null
        ) {
          roles.push(role);
        }
      }
    }
    roles = this.remove_non_user_roles(roles);
    return roles;
  }

  private remove_non_user_roles(roles: Role[]) {
    // remove container and node roles as these are not relevant to the users
    for (let role_name of ['container', 'node']) {
      roles = roles.filter(function (role: any) {
        return role.name !== role_name;
      });
    }
    return roles;
  }

  isDefaultRole(role: Role): boolean {
    return role.organization_id === null;
  }
}
