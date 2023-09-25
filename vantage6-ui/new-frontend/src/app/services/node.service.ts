import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { BaseNode, NodeCreate } from '../models/api/node.model';
import { BaseCollaboration } from '../models/api/collaboration.model';
import { OrganizationService } from './organization.service';

@Injectable({
  providedIn: 'root'
})
export class NodeService {
  constructor(
    private apiService: ApiService,
    private organizationService: OrganizationService
  ) {}

  async createNode(collaboration: BaseCollaboration, organizationID: number): Promise<BaseNode> {
    const organization = await this.organizationService.getOrganization(organizationID.toString());

    const node: NodeCreate = {
      name: `${collaboration.name} - ${organization.name}`,
      organization_id: organizationID,
      collaboration_id: collaboration.id
    };

    return await this.apiService.postForApi<BaseNode>(`/node`, node);
  }
}
