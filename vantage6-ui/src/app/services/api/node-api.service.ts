import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { Node } from 'src/app/interfaces/node';
import { ModalService } from 'src/app/services/common/modal.service';
import { ResType } from 'src/app/shared/enum';
import { BaseApiService } from 'src/app/services/api/base-api.service';
import { environment } from 'src/environments/environment';

/**
 * Service for interacting with the node endpoints of the API
 */
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

  /**
   * Reset the api key of a node via the API.
   *
   * @param node The node to reset the api key for.
   * @returns The new api key, or null if the request failed.
   */
  async reset_api_key(node: Node): Promise<string | null> {
    let data = { id: node.id };
    try {
      let response = await this.http
        .post<any>(environment.api_url + '/recover/node', data)
        .toPromise();
      return response.api_key;
    } catch (error: any) {
      this.modalService.openErrorModal(error.error.msg);
      return null;
    }
  }

  /**
   * Get the data to send to the API for updating or creating a node.
   *
   * @param node The node to get the data for.
   * @returns The data to send to the API.
   */
  get_data(node: Node): any {
    let data: any = {
      name: node.name,
      collaboration_id: node.collaboration_id,
      organization_id: node.organization_id,
    };
    return data;
  }
}
