import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { Collaboration } from 'src/app/interfaces/collaboration';

import { ModalService } from 'src/app/services/common/modal.service';
import { ResType } from 'src/app/shared/enum';
import { getIdsFromArray } from 'src/app/shared/utils';
import { BaseApiService } from 'src/app/services/api/base-api.service';

@Injectable({
  providedIn: 'root',
})
export class CollabApiService extends BaseApiService {
  constructor(
    protected http: HttpClient,
    protected modalService: ModalService
  ) {
    super(ResType.COLLABORATION, http, modalService);
  }

  get_data(resource: Collaboration): any {
    let data: any = {
      name: resource.name,
      encrypted: resource.encrypted,
      organization_ids: getIdsFromArray(resource.organizations),
    };
    return data;
  }
}
