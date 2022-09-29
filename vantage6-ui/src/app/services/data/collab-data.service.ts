import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Collaboration } from 'src/app/interfaces/collaboration';
import {
  Organization,
  OrganizationInCollaboration,
} from 'src/app/interfaces/organization';
import { Node } from 'src/app/interfaces/node';
import { CollabApiService } from '../api/collaboration-api.service';
import { ConvertJsonService } from '../common/convert-json.service';
import { BaseDataService } from './base-data.service';
import { deepcopy } from 'src/app/shared/utils';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { OpsType, ResType } from 'src/app/shared/enum';

@Injectable({
  providedIn: 'root',
})
export class CollabDataService extends BaseDataService {
  constructor(
    protected collabApiService: CollabApiService,
    protected convertJsonService: ConvertJsonService,
    private userPermission: UserPermissionService
  ) {
    super(collabApiService, convertJsonService);
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
    organizations: Organization[] = [],
    nodes: Node[] = [],
    force_refresh: boolean = false
  ): Promise<Collaboration[]> {
    let collaborations = (await super.list_base(
      this.convertJsonService.getCollaboration,
      [organizations],
      force_refresh
    )) as Collaboration[];
    await this.refreshNodes(this.resource_list as Collaboration[], nodes);
    return collaborations;
  }

  async org_list(
    organization_id: number,
    organizations: Organization[] = [],
    nodes: Node[] = [],
    force_refresh: boolean = false
  ): Promise<Collaboration[]> {
    if (
      !this.userPermission.can(
        OpsType.VIEW,
        ResType.COLLABORATION,
        organization_id
      )
    ) {
      return [];
    }
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
      for (let resource of this.resource_list as Collaboration[]) {
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

  async addOrgsAndNodes(
    collabs: Collaboration[],
    organizations: OrganizationInCollaboration[],
    nodes: Node[]
  ): Promise<Collaboration[]> {
    let updated_collabs = [...collabs];

    this.deleteOrgsFromCollaborations(collabs);
    this.addOrgsToCollaborations(collabs, organizations);

    this.deleteNodesFromCollaborations(collabs);
    this.addNodesToCollaborations(collabs, nodes);

    if (JSON.stringify(updated_collabs) !== JSON.stringify(collabs)) {
      this.saveMultiple(collabs);
    }
    return collabs;
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

  addOrgsToCollaborations(
    collabs: Collaboration[],
    orgs: OrganizationInCollaboration[]
  ): void {
    for (let c of collabs) {
      this.addOrgsToCollaboration(c, orgs);
    }
  }

  addOrgsToCollaboration(
    c: Collaboration,
    orgs: OrganizationInCollaboration[]
  ): void {
    for (let org_id of c.organization_ids) {
      for (let org of orgs) {
        if (org.id === org_id) {
          c.organizations.push(deepcopy(org));
        }
      }
    }
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

  deleteOrgsFromCollaborations(collabs: Collaboration[]): void {
    for (let c of collabs) {
      this.deleteOrgsFromCollaboration(c);
    }
  }

  deleteOrgsFromCollaboration(c: Collaboration): void {
    c.organizations = [];
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
