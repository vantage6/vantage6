import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { Organization } from 'src/app/interfaces/organization';
import { environment } from 'src/environments/environment';

@Injectable({
  providedIn: 'root',
})
export class OrganizationService {
  constructor(private http: HttpClient) {}

  list() {}

  get(id: number) {
    return this.http.get(environment.api_url + '/organization/' + id);
  }

  update(id: number, organization: Organization) {}

  create(id: number, organization: Organization) {}

  delete(id: number) {}
}
