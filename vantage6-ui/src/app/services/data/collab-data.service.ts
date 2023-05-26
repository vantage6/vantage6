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
import {
  Pagination,
  allPages,
  defaultFirstPage,
} from 'src/app/interfaces/utils';

@Injectable({
  providedIn: 'root',
})
export class CollabDataService extends BaseDataService {
  nodes: Node[] = [];
  organizations: Organization[] = [];

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
    // TODO don't get all nodes and organizations, but only those that are
    // needed for the current list of collaborations
    (await this.nodeDataService.list(false, allPages())).subscribe((nodes) => {
      this.nodes = nodes;
      this.updateNodes();
    });
    (await this.orgDataService.list(false, allPages())).subscribe((orgs) => {
      this.organizations = orgs;
      this.updateOrganizations();
    });
    return [this.organizations, this.nodes];
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
    include_links: boolean = false,
    force_refresh: boolean = false
  ): Promise<Observable<Collaboration>> {
    let collab = (
      await super.get_base(
        id,
        this.convertJsonService.getCollaboration,
        force_refresh
      )
    )
    if (include_links){
        // include internal resources
    }
    console.log(collab.value)

    return collab.asObservable() as Observable<Collaboration>;
  }

  async list(
    force_refresh: boolean = false,
    pagination: Pagination = defaultFirstPage()
  ): Promise<Observable<Collaboration[]>> {
    let collaborations = (await super.list_base(
      this.convertJsonService.getCollaboration,
      pagination,
      force_refresh
    )) as Observable<Collaboration[]>;
    return collaborations;
  }

  async org_list(
    organization_id: number,
    force_refresh: boolean = false,
    pagination: Pagination = allPages()
  ): Promise<Observable<Collaboration[]>> {
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
      pagination,
      force_refresh
    )) as Observable<Collaboration[]>;
  }

  updateNodes(): void {
    let collabs = deepcopy(this.resource_list.value);
    this.deleteNodesFromCollaborations(collabs);
    this.addNodesToCollaborations(collabs, this.nodes);
    this.resource_list.next(collabs);
  }

  updateOrganizations(): void {
    let collabs = deepcopy(this.resource_list.value);
    this.deleteOrgsFromCollaborations(collabs);
    this.addOrgsToCollaborations(collabs, this.organizations);
    this.resource_list.next(collabs);
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
