import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Collaboration } from 'src/app/interfaces/collaboration';
import { Organization } from 'src/app/interfaces/organization';
import { Node } from 'src/app/interfaces/node';
import { ApiCollaborationService } from '../api/api-collaboration.service';
import { ConvertJsonService } from '../common/convert-json.service';
import { BaseDataService } from './base-data.service';

@Injectable({
  providedIn: 'root',
})
export class CollabDataService extends BaseDataService {
  org_dict: { [org_id: number]: Collaboration[] } = {};

  constructor(
    protected apiCollabService: ApiCollaborationService,
    protected convertJsonService: ConvertJsonService
  ) {
    super(apiCollabService, convertJsonService);
  }

  async get(
    id: number,
    organizations: Organization[] = [],
    nodes: Node[] = [],
    force_refresh: boolean = false
  ): Promise<Collaboration> {
    let collaboration = (await super.get_base(
      id,
      this.convertJsonService.getCollaboration,
      [organizations],
      force_refresh
    )) as Collaboration;
    if (nodes.length > 0) {
      // Delete nodes from collab, then add them back (this updates
      // nodes that were just deleted)
      this.deleteNodesFromCollaboration(collaboration);
      this.addNodesToCollaboration(collaboration, nodes);
    }
    return collaboration;
  }

  async list(
    organizations: Organization[],
    nodes: Node[] = [],
    force_refresh: boolean = false
  ): Promise<Observable<Collaboration[]>> {
    let collaborations = (await super.list_base(
      this.convertJsonService.getCollaboration,
      [organizations],
      force_refresh
    )) as Observable<Collaboration[]>;
    if (nodes.length > 0) {
      // Delete nodes from collabs, then add them back (this updates
      // nodes that were just deleted)
      this.deleteNodesFromCollaborations(
        this.resource_list.value as Collaboration[]
      );
      this.addNodesToCollaborations(
        this.resource_list.value as Collaboration[],
        nodes
      );
    }
    return collaborations;
  }

  async org_list(
    organization_id: number,
    organizations: Organization[],
    nodes: Node[] = [],
    force_refresh: boolean = false
  ): Promise<Collaboration[]> {
    if (
      force_refresh ||
      !(organization_id in this.org_dict) ||
      this.org_dict[organization_id].length === 0
    ) {
      this.org_dict[organization_id] = (await this.apiService.getResources(
        this.convertJsonService.getCollaboration,
        [organizations],
        { organization_id: organization_id }
      )) as Collaboration[];
    }
    if (nodes.length > 0) {
      // Delete nodes from collabs, then add them back (this updates
      // nodes that were just deleted)
      this.deleteNodesFromCollaborations(this.org_dict[organization_id]);
      this.addNodesToCollaborations(this.org_dict[organization_id], nodes);
    }
    return this.org_dict[organization_id];
  }

  addNodesToCollaborations(collabs: Collaboration[], nodes: Node[]): void {
    for (let c of collabs) {
      this.addNodesToCollaboration(c, nodes);
    }
  }

  addNodesToCollaboration(c: Collaboration, nodes: Node[]): void {
    for (let o of c.organizations) {
      for (let n of nodes) {
        if (o.id === n.organization_id && c.id === n.collaboration_id) {
          o.node = n;
        }
      }
    }
  }

  deleteNodesFromCollaborations(collabs: Collaboration[]): void {
    for (let c of collabs) {
      this.deleteNodesFromCollaboration(c);
    }
  }

  deleteNodesFromCollaboration(c: Collaboration): void {
    for (let o of c.organizations) {
      o.node = undefined;
    }
  }
}
