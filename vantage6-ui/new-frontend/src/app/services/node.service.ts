import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { BaseNode, GetNodeParameters, Node, NodeCreate, NodeEdit, NodeLazyProperties } from '../models/api/node.model';
import { BaseCollaboration, Collaboration } from '../models/api/collaboration.model';
import { OrganizationService } from './organization.service';
import { Pagination } from '../models/api/pagination.model';
import { getLazyProperties } from '../helpers/api.helper';

@Injectable({
  providedIn: 'root'
})
export class NodeService {
  constructor(
    private apiService: ApiService,
    private organizationService: OrganizationService
  ) {}

  async getNodes(parameters?: GetNodeParameters): Promise<BaseNode[]> {
    //TODO: Add backend no pagination instead of page size 9999
    const result = await this.apiService.getForApi<Pagination<BaseNode>>('/node', { ...parameters, per_page: 9999 });
    return result.data;
  }

  async getPaginatedNodes(currentPage: number, parameters?: GetNodeParameters): Promise<Pagination<BaseNode>> {
    const result = await this.apiService.getForApiWithPagination<BaseNode>('/node', currentPage, parameters);
    return result;
  }

  async getNode(id: string, lazyProperties: NodeLazyProperties[] = []): Promise<Node> {
    const result = await this.apiService.getForApi<BaseNode>(`/node/${id}`);

    const node: Node = { ...result, organization: undefined, collaboration: undefined };
    await getLazyProperties(result, node, lazyProperties, this.apiService);

    return node;
  }

  async createNode(collaboration: BaseCollaboration | Collaboration, organizationID: number): Promise<BaseNode> {
    const organization = await this.organizationService.getOrganization(organizationID.toString());

    const node: NodeCreate = {
      name: `${collaboration.name} - ${organization.name}`,
      organization_id: organizationID,
      collaboration_id: collaboration.id
    };

    return await this.apiService.postForApi<BaseNode>(`/node`, node);
  }

  async deleteNode(collaboration: BaseCollaboration | Collaboration, organizationID: number): Promise<void> {
    const nodes = await this.getNodes({ organization_id: organizationID.toString(), collaboration_id: collaboration.id.toString() });
    const nodeID = nodes[0].id;
    await this.apiService.deleteForApi(`/node/${nodeID}`);
  }

  async editNode(nodeID: string, nodeEdit: NodeEdit): Promise<BaseNode> {
    return await this.apiService.patchForApi<BaseNode>(`/node/${nodeID}`, nodeEdit);
  }
}
