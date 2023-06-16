import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { NodeApiService } from 'src/app/services/api/node-api.service';
import { ConvertJsonService } from 'src/app/services/common/convert-json.service';
import { BaseDataService } from 'src/app/services/data/base-data.service';
import { Node, NodeWithOrg } from 'src/app/interfaces/node';
import { SocketioConnectService } from '../common/socketio-connect.service';
import {
  Pagination,
  allPages,
  defaultFirstPage,
} from 'src/app/interfaces/utils';

@Injectable({
  providedIn: 'root',
})
export class NodeDataService extends BaseDataService {
  constructor(
    protected apiService: NodeApiService,
    protected convertJsonService: ConvertJsonService,
    private socketService: SocketioConnectService
  ) {
    super(apiService, convertJsonService);
    this.socketService.getNodeStatusUpdates().subscribe((update) => {
      this.updateNodeStatus(update);
    });
  }

  async get(
    id: number,
    force_refresh: boolean = false
  ): Promise<Observable<Node>> {
    return (
      await super.get_base(id, this.convertJsonService.getNode, force_refresh)
    ).asObservable() as Observable<Node>;
  }

  async list(
    force_refresh: boolean = false,
    pagination: Pagination = defaultFirstPage()
  ): Promise<Observable<Node[]>> {
    return (await super.list_base(
      this.convertJsonService.getNode,
      pagination,
      force_refresh
    )).asObservable() as Observable<Node[]>;
  }

  async org_list(
    organization_id: number,
    force_refresh: boolean = false,
    pagination: Pagination = allPages()
  ): Promise<Observable<Node[]>> {
    return (await this.org_list_base(
      organization_id,
      this.convertJsonService.getNode,
      pagination,
      force_refresh
    )).asObservable() as Observable<Node[]>;
  }

  async collab_list(
    collaboration_id: number,
    force_refresh: boolean = false,
    pagination: Pagination = allPages()
  ): Promise<Observable<Node[]>> {
    return (await super.collab_list_base(
      collaboration_id,
      this.convertJsonService.getNode,
      pagination,
      force_refresh
    )) as Observable<Node[]>;
  }

  async list_with_params(
    pagination: Pagination = allPages(),
    request_params: any = {}
  ): Promise<Node[]> {
    return await super.list_with_params_base(
      this.convertJsonService.getNode,
      request_params,
      pagination,
    ) as Node[];
  }

  updateNodeStatus(status_update: any) {
    let resources = this.resource_list.value as Node[];
    for (let r of resources) {
      if (r.id === status_update.id) {
        r.is_online = status_update.online;
      }
    }
    this.resource_list.next(resources);
  }

  save(node: NodeWithOrg) {
    // remove organization and collaboration properties - these should be set
    // within components where needed
    if (node.organization) node.organization = undefined;
    if (node.collaboration) node.collaboration = undefined;
    super.save(node);
  }
}
