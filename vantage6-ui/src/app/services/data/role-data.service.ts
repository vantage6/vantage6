import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Role } from 'src/app/interfaces/role';
import { ApiRoleService } from 'src/app/services/api/api-role.service';
import { ConvertJsonService } from 'src/app/services/common/convert-json.service';
import { Resource } from 'src/app/shared/types';
import { BaseDataService } from 'src/app/services/data/base-data.service';
import { Rule } from 'src/app/interfaces/rule';
import { deepcopy } from 'src/app/shared/utils';

@Injectable({
  providedIn: 'root',
})
export class RoleDataService extends BaseDataService {
  org_roles_dict: { [org_id: number]: Role[] } = {};

  constructor(
    protected apiService: ApiRoleService,
    protected convertJsonService: ConvertJsonService
  ) {
    super(apiService, convertJsonService);
  }

  async get(
    id: number,
    rules: Rule[],
    force_refresh: boolean = false
  ): Promise<Observable<Role>> {
    return (await super.get_base(
      id,
      this.convertJsonService.getRole,
      [rules],
      force_refresh
    )) as Observable<Role>;
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

  async org_list(
    organization_id: number,
    include_root = true,
    force_refresh: boolean = false
  ): Promise<Role[]> {
    if (
      force_refresh ||
      !(organization_id in this.org_roles_dict) ||
      this.org_roles_dict[organization_id].length === 0
    ) {
      this.org_roles_dict[organization_id] =
        await this.apiService.getOrganizationRoles(
          organization_id,
          include_root
        );
    }
    return this.org_roles_dict[organization_id];
  }
}
