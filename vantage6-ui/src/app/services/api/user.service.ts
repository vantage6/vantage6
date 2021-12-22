import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { environment } from 'src/environments/environment';
import { User } from 'src/app/interfaces/user';

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

  update(id: number, user: User) {}

  create(id: number, user: User) {}

  delete(id: number) {}
}
