import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { environment } from 'src/environments/environment';
import {
  Collaboration,
  EMPTY_COLLABORATION,
} from '../interfaces/collaboration';

import { ModalService } from 'src/app/modal/modal.service';
import { ConvertJsonService } from 'src/app/shared/services/convert-json.service';
import { Resource } from 'src/app/shared/enum';
import { getIdsFromArray } from 'src/app/shared/utils';
import { ModalMessageComponent } from 'src/app/modal/modal-message/modal-message.component';
import { Organization } from 'src/app/organization/interfaces/organization';

@Injectable({
  providedIn: 'root',
})
export class ApiCollaborationService {
  collaboration_list: Collaboration[] = [];

  constructor(
    private http: HttpClient,
    private convertJsonService: ConvertJsonService,
    private modalService: ModalService
  ) {}

  list(): any {
    return this.http.get(environment.api_url + '/' + Resource.COLLABORATION);
  }

  get(id: number) {
    return this.http.get(
      environment.api_url + '/' + Resource.COLLABORATION + '/' + id
    );
  }

  update(collaboration: Collaboration) {
    const data = this._get_data(collaboration);
    return this.http.patch<any>(
      environment.api_url +
        '/' +
        Resource.COLLABORATION +
        '/' +
        collaboration.id,
      data
    );
  }

  create(collaboration: Collaboration) {
    const data = this._get_data(collaboration);
    return this.http.post<any>(
      environment.api_url + '/' + Resource.COLLABORATION,
      data
    );
  }

  private _get_data(collaboration: Collaboration): any {
    let data: any = {
      name: collaboration.name,
      encrypted: collaboration.encrypted,
      organization_ids: getIdsFromArray(collaboration.organizations),
    };
    return data;
  }

  async getCollaboration(
    id: number,
    organizations: Organization[]
  ): Promise<Collaboration> {
    let coll_json: any;
    try {
      coll_json = await this.get(id).toPromise();
      return this.convertJsonService.getCollaboration(coll_json, organizations);
    } catch (error: any) {
      this.modalService.openMessageModal(ModalMessageComponent, [
        'Error: ' + error.error.msg,
      ]);
      return EMPTY_COLLABORATION;
    }
  }

  async getCollaborations(
    organizations: Organization[],
    force_refresh: boolean = false
  ): Promise<Collaboration[]> {
    if (!force_refresh && this.collaboration_list.length > 0) {
      return this.collaboration_list;
    }
    // get data of organization that logged-in user is allowed to view
    let data = await this.list().toPromise();

    // set organization data
    this.collaboration_list = [];
    for (let coll of data) {
      this.collaboration_list.push(
        this.convertJsonService.getCollaboration(coll, organizations)
      );
    }
    return this.collaboration_list;
  }
}
