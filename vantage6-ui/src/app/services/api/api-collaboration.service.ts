import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import {
  Collaboration,
  EMPTY_COLLABORATION,
} from 'src/app/interfaces/collaboration';

import { ModalService } from 'src/app/modal/modal.service';
import { ConvertJsonService } from 'src/app/shared/services/convert-json.service';
import { ResType } from 'src/app/shared/enum';
import { getIdsFromArray } from 'src/app/shared/utils';
import { Organization } from 'src/app/interfaces/organization';
import { ApiService } from 'src/app/services/api/api.service';

@Injectable({
  providedIn: 'root',
})
export class ApiCollaborationService extends ApiService {
  collaboration_list: Collaboration[] = [];

  constructor(
    protected http: HttpClient,
    private convertJsonService: ConvertJsonService,
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

  async getCollaboration(
    id: number,
    organizations: Organization[]
  ): Promise<Collaboration> {
    let col = await super.getResource(
      id,
      this.convertJsonService.getCollaboration,
      [organizations]
    );
    return col === null ? EMPTY_COLLABORATION : col;
  }

  async getCollaborations(
    organizations: Organization[],
    force_refresh: boolean = false
  ): Promise<Collaboration[]> {
    return await super.getResources(
      force_refresh,
      this.convertJsonService.getCollaboration,
      [organizations]
    );
  }
}
