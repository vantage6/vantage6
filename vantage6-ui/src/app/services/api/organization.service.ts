import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { Organization } from 'src/app/interfaces/organization';
import { environment } from 'src/environments/environment';

@Injectable({
  providedIn: 'root',
})
export class OrganizationService {
  constructor(private http: HttpClient) {}

  list() {
    return this.http.get(environment.api_url + '/organization');
  }

  get(id: number) {
    return this.http.get(environment.api_url + '/organization/' + id);
  }

  update(org: Organization) {
    const data = this._get_data(org);
    return this.http.patch<any>(
      environment.api_url + '/organization/' + org.id,
      data
    );
  }

  create(org: Organization) {
    const data = this._get_data(org);
    return this.http.post<any>(environment.api_url + '/organization', data);
  }

  private _get_data(org: Organization): any {
    let data: any = {
      name: org.name,
      address1: org.address1,
      address2: org.address2,
      zipcode: org.zipcode,
      country: org.country,
      domain: org.domain,
      public_key: org.public_key,
    };
    return data;
  }
}
