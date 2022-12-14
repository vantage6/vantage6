import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { RoleApiService } from 'src/app/services/api/role-api.service';
import { ConvertJsonService } from 'src/app/services/common/convert-json.service';
import { BaseDataService } from 'src/app/services/data/base-data.service';
import { Resource } from 'src/app/shared/types';
import {
  arrayContains,
  filterArrayByProperty,
  getIdsFromArray,
  unique,
} from 'src/app/shared/utils';
import { RuleDataService } from './rule-data.service';

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

  async getDependentResources(): Promise<Resource[][]> {
    (await this.ruleDataService.list()).subscribe((rules) => {
      this.rules = rules;
      // TODO when rules change, update roles as well
    });
    return [this.rules];
  }

  updateObsPerOrg(resources: Resource[]) {
    // This overwrites the super() method to ensure that default roles
    // (with organization_id=null) are also included in each organization
    if (!this.requested_org_lists) return;
    for (let org_id of this.requested_org_lists) {
      if (org_id in this.resources_per_org) {
        this.resources_per_org[org_id].next(
          this.getRolesForOrgId(resources as Role[], org_id)
        );
      } else {
        this.resources_per_org[org_id] = new BehaviorSubject<Resource[]>(
          this.getRolesForOrgId(resources as Role[], org_id)
        );
      }
    }
  }

  private getRolesForOrgId(roles: Role[], org_id: number): Role[] {
    let org_resources: Role[] = [];
    for (let r of roles) {
      if (r.organization_id === org_id || r.organization_id === null) {
        org_resources.push(r);
      }
    }
    org_resources = this.remove_non_user_roles(org_resources);
    return org_resources;
  }

  async get(
    id: number,
    force_refresh: boolean = false
  ): Promise<Observable<Role>> {
    return (await super.get_base(
      id,
      this.convertJsonService.getRole,
      force_refresh
    )) as Observable<Role>;
  }

  async list(force_refresh: boolean = false): Promise<Observable<Role[]>> {
    return (await super.list_base(
      this.convertJsonService.getRole,
      force_refresh
    )) as Observable<Role[]>;
  }

  async list_with_params(request_params: any = {}): Promise<Role[]> {
    return (await super.list_with_params_base(
      this.convertJsonService.getRole,
      request_params
    )) as Role[];
  }

  async org_list(
    organization_id: number,
    force_refresh: boolean = false
  ): Promise<Observable<Role[]>> {
    return (await super.org_list_base(
      organization_id,
      this.convertJsonService.getRole,
      force_refresh,
      { include_root: true }
    )) as Observable<Role[]>;
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
