import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';

import { getIdsFromArray } from 'src/app/utils';
import { environment } from 'src/environments/environment';
import { ConvertJsonService } from '../convert-json.service';
import { RuleService } from './rule.service';

@Injectable({
  providedIn: 'root',
})
export class RoleService {
  all_rules: Rule[] = [];

  constructor(
    private http: HttpClient,
    private ruleService: RuleService,
    private convertJsonService: ConvertJsonService
  ) {
    this.setup();
  }

  async setup(): Promise<void> {
    this.all_rules = await this.ruleService.getAllRules();
  }

  list(organization_id: number | null = null, include_root: boolean = false) {
    let params: any = {};
    if (organization_id !== null) {
      params['organization_id'] = organization_id;
    }
    params['include_root'] = include_root;
    return this.http.get(environment.api_url + '/role', { params: params });
  }

  get(id: number) {
    return this.http.get<any>(environment.api_url + '/role/' + id);
  }

  update(role: Role) {
    const data = this._get_data(role);
    return this.http.patch<any>(environment.api_url + '/role/' + role.id, data);
  }

  create(role: Role) {
    const data = this._get_data(role);
    return this.http.post<any>(environment.api_url + '/role', data);
  }

  delete(role: Role) {
    return this.http.delete<any>(environment.api_url + '/role/' + role.id);
  }

  private _get_data(role: Role): any {
    return {
      name: role.name,
      description: role.description,
      organization_id: role.organization_id,
      rules: getIdsFromArray(role.rules),
    };
  }

  async getRole(id: number): Promise<Role> {
    if (this.all_rules.length === 0) {
      await this.setup();
    }
    let role_json = await this.get(id).toPromise();
    return this.convertJsonService.getRole(role_json, this.all_rules);
  }

  async getRoles(ids: number[]): Promise<Role[]> {
    let roles: Role[] = [];
    for (let id of ids) {
      roles.push(await this.getRole(id));
    }
    return roles;
  }
}
