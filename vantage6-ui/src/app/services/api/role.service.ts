import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { Role } from 'src/app/interfaces/role';
import { environment } from 'src/environments/environment';

@Injectable({
  providedIn: 'root',
})
export class RoleService {
  constructor(private http: HttpClient) {}

  list() {}

  get(id: number) {
    return this.http.get<any>(environment.api_url + '/role/' + id);
  }

  update(id: number, role: Role) {}

  create(id: number, role: Role) {}

  delete(id: number) {}
}
