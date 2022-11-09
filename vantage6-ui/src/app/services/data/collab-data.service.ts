import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { Collaboration } from 'src/app/interfaces/collaboration';
import {
  Organization,
  OrganizationInCollaboration,
} from 'src/app/interfaces/organization';
import { Node } from 'src/app/interfaces/node';
import { CollabApiService } from '../api/collaboration-api.service';
import { ConvertJsonService } from '../common/convert-json.service';
import { BaseDataService } from './base-data.service';
import { arrayContains, deepcopy } from 'src/app/shared/utils';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { OpsType, ResType } from 'src/app/shared/enum';
import { NodeDataService } from './node-data.service';
import { OrgDataService } from './org-data.service';
import { Resource } from 'src/app/shared/types';

@Injectable({
  providedIn: 'root',
})
export class CollabDataService extends BaseDataService {
  nodes: Node[] = [];
  organizations: Organization[] = [];
  requested_org_lists: number[] = [];

  constructor(
    protected collabApiService: CollabApiService,
    protected convertJsonService: ConvertJsonService,
    private userPermission: UserPermissionService,
    private nodeDataService: NodeDataService,
    private orgDataService: OrgDataService
  ) {
    super(collabApiService, convertJsonService);
    this.resource_list.subscribe((resources) => {
      // When the list of all resources is updated, ensure that sublists of
      // observables are also updated

      // update the observables per org
      this.updateObsPerOrg(resources);

      // update observables that are gotten one by one
      this.updateObsById(resources);

      // update the observables per collab
      this.updateObsPerCollab(resources);
    });
  }

  async getDependentResources() {
    (await this.nodeDataService.list()).subscribe((nodes) => {
      this.nodes = nodes;
      // TODO refresh lists
    });
    (await this.orgDataService.list()).subscribe((orgs) => {
      this.organizations = orgs;
      // TODO refresh lists
    });
  }

  updateObsPerOrg(resources: Resource[]) {
    // collaborations should be updated in slightly different way from super
    // function as they contain multiple organizations and also (as consequence)
    // we could also have incomplete data for specific organizations
    if (!this.requested_org_lists) return;
    for (let org_id of this.requested_org_lists) {
      if (org_id in this.resources_per_org) {
        this.resources_per_org[org_id].next(
          this.getCollabsForOrgId(resources as Collaboration[], org_id)
        );
      } else {
        this.resources_per_org[org_id] = new BehaviorSubject<Resource[]>(
          this.getCollabsForOrgId(resources as Collaboration[], org_id)
        );
      }
    }
  }

  private getCollabsForOrgId(
    resources: Collaboration[],
    org_id: number
  ): Resource[] {
    let org_resources: Resource[] = [];
    for (let r of resources) {
      if (arrayContains(r.organization_ids, org_id)) {
        org_resources.push(r);
      }
    }
    return org_resources;
  }

  async get(
    id: number,
    force_refresh: boolean = false
  ): Promise<Observable<Collaboration>> {
    await this.getDependentResources();
    return (await super.get_base(
      id,
      this.convertJsonService.getCollaboration,
      [this.organizations, this.nodes],
      force_refresh
    )) as Observable<Collaboration>;
  }

  async list(
    organizations: Organization[] = [],
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
    force_refresh: boolean = false
  ): Promise<Observable<Collaboration[]>> {
    if (!arrayContains(this.requested_org_lists, organization_id)) {
      this.requested_org_lists.push(organization_id);
    }
    // TODO when is following if statement necessary?
    if (
      !this.userPermission.can(
        OpsType.VIEW,
        ResType.COLLABORATION,
        organization_id
      )
    ) {
      return of([]);
    }
    return (await super.org_list_base(
      organization_id,
      this.convertJsonService.getCollaboration,
      [this.organizations, this.nodes],
      force_refresh
    )) as Observable<Collaboration[]>;
  }

  // TODO what to do with this?
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
