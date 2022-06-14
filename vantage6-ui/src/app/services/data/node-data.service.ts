import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiNodeService } from 'src/app/services/api/api-node.service';
import { ConvertJsonService } from 'src/app/services/common/convert-json.service';
import { BaseDataService } from 'src/app/services/data/base-data.service';
import { Node } from 'src/app/interfaces/node';

@Injectable({
  providedIn: 'root',
})
export class NodeDataService extends BaseDataService {
  org_dict: { [org_id: number]: Node[] } = {};
  collab_dict: { [collab_id: number]: Node[] } = {};

  constructor(
    protected apiService: ApiNodeService,
    protected convertJsonService: ConvertJsonService
  ) {
    super(apiService, convertJsonService);
  }

  async get(id: number, force_refresh: boolean = false): Promise<Node> {
    return (await super.get_base(
      id,
      this.convertJsonService.getNode,
      [],
      force_refresh
    )) as Node;
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
  ): Promise<Node[]> {
    if (
      force_refresh ||
      !(organization_id in this.org_dict) ||
      this.org_dict[organization_id].length === 0
    ) {
      this.org_dict[organization_id] = (await this.apiService.getResources(
        this.convertJsonService.getNode,
        [],
        { organization_id: organization_id }
      )) as Node[];
    }
    return this.org_dict[organization_id];
  }

  async collab_list(
    collaboration_id: number,
    force_refresh: boolean = false
  ): Promise<Node[]> {
    if (
      force_refresh ||
      !(collaboration_id in this.collab_dict) ||
      this.collab_dict[collaboration_id].length === 0
    ) {
      this.collab_dict[collaboration_id] = (await this.apiService.getResources(
        this.convertJsonService.getNode,
        [],
        { collaboration_id: collaboration_id }
      )) as Node[];
    }
    return this.collab_dict[collaboration_id];
  }
}
