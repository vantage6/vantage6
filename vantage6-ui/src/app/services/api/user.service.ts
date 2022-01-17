import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { environment } from 'src/environments/environment';
import { User } from 'src/app/interfaces/user';
import { getIdsFromArray } from 'src/app/utils';

@Injectable({
  providedIn: 'root',
})
export class UserService {
  constructor(private http: HttpClient) {}

  list(organization_id: number | null = null) {
    let params: any = {};
    if (organization_id !== null) {
      params['organization_id'] = organization_id;
    }
    return this.http.get(environment.api_url + '/user', { params: params });
  }

  get(id: number) {
    return this.http.get<any>(environment.api_url + '/user/' + id);
  }

  update(user: User) {
    let data = {
      username: user.username,
      email: user.email,
      firstname: user.first_name,
      lastname: user.last_name,
      organization_id: user.organization_id,
      roles: getIdsFromArray(user.roles),
      rules: getIdsFromArray(user.rules),
    };
    return this.http.patch<any>(environment.api_url + '/user/' + user.id, data);
  }

  create(user: User) {
    const data = {
      username: user.username,
      email: user.email,
      password: user.password,
      firstname: user.first_name,
      lastname: user.last_name,
      organization_id: user.organization_id,
      roles: getIdsFromArray(user.roles),
      rules: getIdsFromArray(user.rules),
    };
    return this.http.post<any>(environment.api_url + '/user', data);
  }

  delete(user: User) {}
}
