import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { Node } from 'src/app/interfaces/node';

import { ModalService } from 'src/app/services/common/modal.service';
import { ResType } from 'src/app/shared/enum';
import { BaseApiService } from 'src/app/services/api/base-api.service';
import { environment } from 'src/environments/environment';
import { ModalMessageComponent } from 'src/app/components/modal/modal-message/modal-message.component';

@Injectable({
  providedIn: 'root',
})
export class NodeApiService extends BaseApiService {
  constructor(
    protected http: HttpClient,
    protected modalService: ModalService
  ) {
    super(ResType.NODE, http, modalService);
  }

  async reset_api_key(node: Node): Promise<string | null> {
    let data = { id: node.id };
    try {
      let response = await this.http
        .post<any>(environment.api_url + '/recover/node', data)
        .toPromise();
      return response.api_key;
    } catch (error: any) {
      this.modalService.openMessageModal(ModalMessageComponent, [
        'Error: ' + error.error.msg,
      ]);
      return null;
    }
  }

  get_data(node: Node): any {
    let data: any = {
      name: node.name,
      collaboration_id: node.collaboration_id,
      organization_id: node.organization_id,
    };
    return data;
  }
}
