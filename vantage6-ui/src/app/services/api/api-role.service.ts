import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';

import { getIdsFromArray } from 'src/app/shared/utils';
import { environment } from 'src/environments/environment';
import { ConvertJsonService } from 'src/app/services/common/convert-json.service';
import { ApiRuleService } from 'src/app/services/api/api-rule.service';
import { ApiService } from 'src/app/services/api/api.service';
import { ResType } from 'src/app/shared/enum';
import { ModalService } from 'src/app/services/common/modal.service';
import { RuleDataService } from '../data/rule-data.service';

// TODO this service is quite different from the other API services
// See to it that this is standardized somewhat, e.g. by obtaining the Rules
// from elsewhere
@Injectable({
  providedIn: 'root',
})
export class ApiRoleService extends ApiService {
  rules: Rule[] = [];

  constructor(
    protected http: HttpClient,
    private ruleDataService: RuleDataService,
    private convertJsonService: ConvertJsonService,
    protected modalService: ModalService
  ) {
    super(ResType.ROLE, http, modalService);
    this.setup();
  }

  async setup(): Promise<void> {
    (await this.ruleDataService.list()).subscribe((rules: Rule[]) => {
      this.rules = rules;
    });
  }

  list(
    organization_id: number | null = null,
    include_root: boolean = false
  ): any {
    let params: any = {};
    if (organization_id !== null) {
      params['organization_id'] = organization_id;
    }
    params['include_root'] = include_root;
    return this.http.get(environment.api_url + '/role', { params: params });
  }

  get_data(role: Role): any {
    return {
      name: role.name,
      description: role.description,
      organization_id: role.organization_id,
      rules: getIdsFromArray(role.rules),
    };
  }

  async getRole(id: number): Promise<Role> {
    if (this.rules.length === 0) {
      await this.setup();
    }
    let role_json = await this.get(id).toPromise();
    return this.convertJsonService.getRole(role_json, this.rules);
  }

  async getRoles(ids: number[]): Promise<Role[]> {
    let roles: Role[] = [];
    for (let id of ids) {
      roles.push(await this.getRole(id));
    }
    return roles;
  }

  async getOrganizationRoles(
    org_id: number,
    include_root: boolean = false
  ): Promise<Role[]> {
    let role_json = await this.list(org_id, include_root).toPromise();
    let roles: Role[] = [];
    for (let role of role_json) {
      roles.push(this.convertJsonService.getRole(role, this.rules));
    }
    return roles;
  }
}
