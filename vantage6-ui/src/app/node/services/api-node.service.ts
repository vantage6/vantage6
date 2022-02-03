import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { EMPTY_NODE, Node } from 'src/app/node/interfaces/node';
import { environment } from 'src/environments/environment';

import { ConvertJsonService } from 'src/app/shared/services/convert-json.service';
import { ModalService } from 'src/app/modal/modal.service';
import { Resource } from 'src/app/shared/enum';
import { ModalMessageComponent } from 'src/app/modal/modal-message/modal-message.component';

@Injectable({
  providedIn: 'root',
})
export class ApiNodeService {
  node_list: Node[] = [];

  constructor(
    private http: HttpClient,
    private convertJsonService: ConvertJsonService,
    private modalService: ModalService
  ) {}

  list(): any {
    return this.http.get(environment.api_url + '/' + Resource.NODE);
  }

  get(id: number) {
    return this.http.get(environment.api_url + '/' + Resource.NODE + '/' + id);
  }

  update(node: Node) {
    const data = this._get_data(node);
    return this.http.patch<any>(
      environment.api_url + '/' + Resource.NODE + '/' + node.id,
      data
    );
  }

  create(node: Node) {
    const data = this._get_data(node);
    return this.http.post<any>(environment.api_url + '/' + Resource.NODE, data);
  }

  private _get_data(node: Node): any {
    let data: any = {
      name: node.name,
    };
    return data;
  }

  async getNode(id: number): Promise<Node> {
    let node_json: any;
    try {
      node_json = await this.get(id).toPromise();
      return this.convertJsonService.getNode(node_json);
    } catch (error: any) {
      this.modalService.openMessageModal(ModalMessageComponent, [
        'Error: ' + error.error.msg,
      ]);
      return EMPTY_NODE;
    }
  }

  async getNodes(force_refresh: boolean = false): Promise<Node[]> {
    if (!force_refresh && this.node_list.length > 0) {
      return this.node_list;
    }
    // get data of nodes that logged-in user is allowed to view
    let node_data = await this.list().toPromise();

    // set nodes
    this.node_list = [];
    for (let node of node_data) {
      this.node_list.push(this.convertJsonService.getNode(node));
    }
    return this.node_list;
  }
}
