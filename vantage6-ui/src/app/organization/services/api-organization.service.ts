import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { EMPTY_ORGANIZATION, Organization } from '../interfaces/organization';
import { ModalMessageComponent } from 'src/app/modal/modal-message/modal-message.component';
import { ModalService } from 'src/app/modal/modal.service';
import { environment } from 'src/environments/environment';
import { ConvertJsonService } from 'src/app/shared/services/convert-json.service';

@Injectable({
  providedIn: 'root',
})
export class ApiOrganizationService {
  organization_list: Organization[] = [];

  constructor(
    private http: HttpClient,
    private convertJsonService: ConvertJsonService,
    private modalService: ModalService
  ) {}

  list(): any {
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

  async getOrganization(id: number): Promise<Organization> {
    let org_json: any;
    try {
      org_json = await this.get(id).toPromise();
      return this.convertJsonService.getOrganization(org_json);
    } catch (error: any) {
      this.modalService.openMessageModal(ModalMessageComponent, [
        'Error: ' + error.error.msg,
      ]);
      return EMPTY_ORGANIZATION;
    }
  }

  async getOrganizations(
    force_refresh: boolean = false
  ): Promise<Organization[]> {
    if (!force_refresh && this.organization_list.length > 0) {
      return this.organization_list;
    }
    // get data of organization that logged-in user is allowed to view
    let org_data = await this.list().toPromise();

    // set organization data
    this.organization_list = [];
    for (let org of org_data) {
      this.organization_list.push(this.convertJsonService.getOrganization(org));
    }
    return this.organization_list;
  }
}
