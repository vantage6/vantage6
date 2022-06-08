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
  constructor(
    protected apiCollabService: ApiCollaborationService,
    protected convertJsonService: ConvertJsonService
  ) {
    super(apiCollabService, convertJsonService);
  }

  async get(
    id: number,
    organizations: Organization[],
    force_refresh: boolean = false
  ): Promise<Collaboration> {
    return (await super.get_base(
      id,
      this.convertJsonService.getCollaboration,
      [organizations],
      force_refresh
    )) as Collaboration;
  }

  async list(
    organizations: Organization[],
    nodes: Node[],
    force_refresh: boolean = false
  ): Promise<Observable<Collaboration[]>> {
    let collaborations = (await super.list_base(
      this.convertJsonService.getCollaboration,
      [organizations],
      force_refresh
    )) as Observable<Collaboration[]>;
    // Delete nodes from collabs, then add them back (this updates
    // nodes that were just deleted)
    this.deleteNodesFromCollaborations();
    this.addNodesToCollaborations(nodes);
    return collaborations;
  }

  addNodesToCollaborations(nodes: Node[]): void {
    for (let c of this.resource_list.value) {
      this.addNodesToCollaboration(c as Collaboration, nodes);
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

  deleteNodesFromCollaborations(): void {
    for (let c of this.resource_list.value) {
      this.deleteNodesFromCollaboration(c as Collaboration);
    }
  }

  deleteNodesFromCollaboration(c: Collaboration): void {
    for (let o of c.organizations) {
      o.node = undefined;
    }
  }
}
