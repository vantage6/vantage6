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
    await this.refreshNodes([collaboration], nodes);
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
    await this.refreshNodes(this.resource_list.value as Collaboration[], nodes);
    return collaborations;
  }

  async org_list(
    organization_id: number,
    organizations: Organization[],
    nodes: Node[] = [],
    force_refresh: boolean = false
  ): Promise<Collaboration[]> {
    let org_resources: Collaboration[] = [];
    if (force_refresh || !this.queried_org_ids.includes(organization_id)) {
      org_resources = (await this.apiService.getResources(
        this.convertJsonService.getCollaboration,
        [organizations],
        { organization_id: organization_id }
      )) as Collaboration[];
      this.queried_org_ids.push(organization_id);
      this.saveMultiple(org_resources);
    } else {
      // this organization has been queried before: get matches from the saved
      // data
      for (let resource of this.resource_list.value as Collaboration[]) {
        if (
          (resource as Collaboration).organization_ids.includes(organization_id)
        ) {
          org_resources.push(resource);
        }
      }
    }
    await this.refreshNodes(org_resources, nodes);
    return org_resources;
  }

  async refreshNodes(collabs: Collaboration[], nodes: Node[]) {
    // Delete nodes from collabs, then add them back (this updates
    // nodes that were just deleted)
    if (nodes.length > 0) {
      this.deleteNodesFromCollaborations(collabs);
      this.addNodesToCollaborations(collabs, nodes);
    }
    // save the updated collaborations
    this.saveMultiple(collabs);
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
