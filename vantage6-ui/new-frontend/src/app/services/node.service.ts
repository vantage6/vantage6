import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { BaseNode, GetNodeParameters, Node, NodeCreate, NodeEdit, NodeLazyProperties, NodeSortProperties } from '../models/api/node.model';
import { BaseCollaboration, Collaboration } from '../models/api/collaboration.model';
import { OrganizationService } from './organization.service';
import { Pagination } from '../models/api/pagination.model';

@Injectable({
  providedIn: 'root'
})
export class NodeService {
  constructor(
    private apiService: ApiService,
    private organizationService: OrganizationService
  ) {}

  async getNodes(sortProperty: NodeSortProperties = NodeSortProperties.ID): Promise<BaseNode[]> {
    const result = await this.apiService.getForApi<Pagination<BaseNode>>('/node', { sort: sortProperty });
    return result.data;
  }

  async getPaginatedNodes(currentPage: number, parameters: GetNodeParameters): Promise<Pagination<BaseNode>> {
    const result = await this.apiService.getForApiWithPagination<BaseNode>('/node', currentPage, parameters);
    return result;
  }

  async getNode(id: string, lazyProperties: NodeLazyProperties[] = []): Promise<Node> {
    const result = await this.apiService.getForApi<BaseNode>(`/node/${id}`);

    const node: Node = { ...result, organization: undefined, collaboration: undefined };

    await Promise.all(
      (lazyProperties as string[]).map(async (lazyProperty) => {
        if (!(result as any)[lazyProperty]) return;

        if ((result as any)[lazyProperty].hasOwnProperty('link') && (result as any)[lazyProperty].link) {
          const resultProperty = await this.apiService.getForApi<any>((result as any)[lazyProperty].link);
          (node as any)[lazyProperty] = resultProperty;
        } else {
          const resultProperty = await this.apiService.getForApi<Pagination<any>>((result as any)[lazyProperty] as string);
          (node as any)[lazyProperty] = resultProperty.data;
        }
      })
    );

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

  async editNode(nodeID: string, nodeEdit: NodeEdit): Promise<BaseNode> {
    return await this.apiService.patchForApi<BaseNode>(`/node/${nodeID}`, nodeEdit);
  }
}
