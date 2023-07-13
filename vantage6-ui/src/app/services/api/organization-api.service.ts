import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { Organization } from 'src/app/interfaces/organization';
import { ModalService } from 'src/app/services/common/modal.service';
import { BaseApiService } from 'src/app/services/api/base-api.service';
import { ResType } from 'src/app/shared/enum';

/**
 * Service for interacting with the organization endpoints of the API
 */
@Injectable({
  providedIn: 'root',
})
export class OrganizationApiService extends BaseApiService {
  organization_list: Organization[] = [];

  constructor(
    protected http: HttpClient,
    protected modalService: ModalService
  ) {
    super(ResType.ORGANIZATION, http, modalService);
  }

  /**
   * Get the data to send to the server when creating or updating an
   * organization.
   *
   * @param org The organization to get the data for.
   * @returns The data to send to the server.
   */
  get_data(org: Organization): any {
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
