import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { Role } from 'src/app/interfaces/role';
import { getIdsFromArray } from 'src/app/utils';
import { environment } from 'src/environments/environment';

@Injectable({
  providedIn: 'root',
})
export class RoleService {
  constructor(private http: HttpClient) {}

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
}
