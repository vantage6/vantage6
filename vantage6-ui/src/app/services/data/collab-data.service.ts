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
import { Resource } from 'src/app/shared/types';
import {
  Pagination,
  allPages,
  defaultFirstPage,
} from 'src/app/interfaces/utils';
import { OrgDataService } from './org-data.service';
import { NodeDataService } from './node-data.service';

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
    private orgDataService: OrgDataService,
    private nodeDataService: NodeDataService,
  ) {
    super(collabApiService, convertJsonService);
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
    ) as BehaviorSubject<Collaboration>;
    if (include_links) {
      let collab_val = collab.value;
      // request the organizations for the current collaboration
      (await this.orgDataService.list_with_params(
        allPages(),
        { collaboration_id: collab_val.id }
      )).subscribe((orgs) => {
        collab_val.organizations = orgs;
      });
      // request the nodes for the current collaboration
      (await this.nodeDataService.list_with_params(allPages(), {
        collaboration_id: collab_val.id,
      })).subscribe((nodes) => {
        this.addNodesToCollaboration(collab_val, nodes);
      });
    }
    return collab.asObservable() as Observable<Collaboration>;
  }

  async list(
    force_refresh: boolean = false,
    pagination: Pagination = defaultFirstPage()
  ): Promise<Observable<Collaboration[]>> {
    return (await super.list_base(
      this.convertJsonService.getCollaboration,
      pagination,
      force_refresh
    )).asObservable() as Observable<Collaboration[]>;
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
    )).asObservable() as Observable<Collaboration[]>;
  }

  async list_with_params(
    pagination: Pagination = allPages(),
    request_params: any = {}
  ): Promise<Observable<Collaboration[]>> {
    return (await super.list_with_params_base(
      this.convertJsonService.getCollaboration,
      request_params,
      pagination,
    )).asObservable() as Observable<Collaboration[]>;
  }

  updateNodes(collabs: Collaboration[]): void {
    this.deleteNodesFromCollaborations(collabs);
    this.addNodesToCollaborations(collabs, this.nodes);
  }

  updateOrganizations(collabs: Collaboration[]): void {
    this.deleteOrgsFromCollaborations(collabs);
    this.addOrgsToCollaborations(collabs, this.organizations);
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
