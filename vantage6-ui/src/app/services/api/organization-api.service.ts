import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { Organization } from 'src/app/interfaces/organization';
import { ModalService } from 'src/app/services/common/modal.service';
import { ApiService } from 'src/app/services/api/api.service';
import { ResType } from 'src/app/shared/enum';

@Injectable({
  providedIn: 'root',
})
export class OrganizationApiService extends ApiService {
  organization_list: Organization[] = [];

  constructor(
    protected http: HttpClient,
    protected modalService: ModalService
  ) {
    super(ResType.ORGANIZATION, http, modalService);
  }

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
