import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of } from 'rxjs';

import { NodeApiService } from 'src/app/services/api/node-api.service';
import { ConvertJsonService } from 'src/app/services/common/convert-json.service';
import { BaseDataService } from 'src/app/services/data/base-data.service';
import { Node } from 'src/app/interfaces/node';
import { SocketioService } from '../common/socketio.service';
import { Resource, ResourceInOrg } from 'src/app/shared/types';
import { filterArrayByProperty } from 'src/app/shared/utils';

@Injectable({
  providedIn: 'root',
})
export class NodeDataService extends BaseDataService {
  constructor(
    protected apiService: NodeApiService,
    protected convertJsonService: ConvertJsonService,
    private socketService: SocketioService
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
    return (await super.get_base(
      id,
      this.convertJsonService.getNode,
      [],
      force_refresh
    )) as Observable<Node>;
  }

  async list(force_refresh: boolean = false): Promise<Observable<Node[]>> {
    return (await super.list_base(
      this.convertJsonService.getNode,
      [],
      force_refresh
    )) as Observable<Node[]>;
  }

  async org_list(
    organization_id: number,
    force_refresh: boolean = false
  ): Promise<Observable<Node[]>> {
    return (await this.org_list_base(
      organization_id,
      this.convertJsonService.getNode,
      [],
      force_refresh
    )) as Observable<Node[]>;
  }

  async collab_list(
    collaboration_id: number,
    force_refresh: boolean = false
  ): Promise<Observable<Node[]>> {
    return (await super.collab_list_base(
      collaboration_id,
      this.convertJsonService.getNode,
      [],
      force_refresh
    )) as Observable<Node[]>;
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
}
