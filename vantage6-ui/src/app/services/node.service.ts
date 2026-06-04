import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import {
  APIKey,
  ApiKeyExport,
  BaseNode,
  GetNodeParameters,
  Node,
  NodeCreate,
  NodeEdit,
  NodeLazyProperties
} from 'src/app/models/api/node.model';
import { BaseCollaboration, Collaboration } from 'src/app/models/api/collaboration.model';
import { OrganizationService } from './organization.service';
import { Pagination } from 'src/app/models/api/pagination.model';
import { getLazyProperties } from 'src/app/helpers/api.helper';
import { BaseOrganization, Organization } from 'src/app/models/api/organization.model';
import { FileService } from './file.service';
import { TranslateService } from '@ngx-translate/core';
import { MatDialog } from '@angular/material/dialog';
import { MessageDialogComponent } from '../components/dialogs/message-dialog/message-dialog.component';

@Injectable({
  providedIn: 'root'
})
export class NodeService {
  constructor(
    private apiService: ApiService,
    private organizationService: OrganizationService,
    private dialog: MatDialog,
    private translateService: TranslateService,
    private fileService: FileService
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
      // ensure no spaces in node name as that would make it an invalid keycloak username
      name: `${collaboration.name}-${organization.name}-node`.replace(/ /g, '-'),
      organization_id: organizationID,
      collaboration_id: collaboration.id
    };

    return await this.apiService.postForApi<BaseNode>(`/node`, node);
  }

  async deleteNode(collaboration: BaseCollaboration | Collaboration, organizationID: number): Promise<void> {
    const nodes = await this.getNodes({ organization_id: organizationID.toString(), collaboration_id: collaboration.id.toString() });
    const nodeID = nodes[0].id;
    await this.apiService.deleteForApi(`/node/${nodeID}?delete_dependents=true`);
  }

  async editNode(nodeID: string, nodeEdit: NodeEdit): Promise<BaseNode> {
    return await this.apiService.patchForApi<BaseNode>(`/node/${nodeID}`, nodeEdit);
  }

  async resetApiKey(nodeID: string): Promise<APIKey> {
    return await this.apiService.postForApi<APIKey>(`/recover/node`, { id: nodeID });
  }

  async registerNodes(
    collaborations: BaseCollaboration[] | Collaboration[],
    organizations: BaseOrganization[] | Organization[],
    fromCollabFirstPerspective: boolean
  ): Promise<void> {
    const apiKeys: ApiKeyExport[] = [];
    const promises: Promise<void>[] = [];

    for (const collaboration of collaborations) {
      for (const organization of organizations) {
        const promise = this.createNode(collaboration, organization.id).then((node) => {
          if (node?.api_key) {
            apiKeys.push({
              entityName: fromCollabFirstPerspective ? organization.name : collaboration.name,
              api_key: node.api_key
            });
          }
        });
        promises.push(promise);
      }
    }

    await Promise.all(promises);
    const entityNameInFile = fromCollabFirstPerspective ? collaborations[0].name : organizations[0].name;
    this.downloadApiKeys(apiKeys, entityNameInFile);
  }

  private downloadApiKeys(api_keys: ApiKeyExport[], collaboration_name: string): void {
    if (api_keys.length === 0) {
      return;
    }
    const filename = `API_keys_${collaboration_name}.txt`;
    const text = api_keys.map((api_key) => `${api_key.entityName}: ${api_key.api_key}`).join('\n');
    this.fileService.downloadTxtFile(text, filename);
    this.alertApiKeyDownload();
  }

  alertApiKeyDownload(): void {
    this.dialog.open(MessageDialogComponent, {
      data: {
        title: this.translateService.instant('api-key-download-dialog.title'),
        content: [
          this.translateService.instant('api-key-download-dialog.create-message'),
          this.translateService.instant('api-key-download-dialog.security-message')
        ],
        confirmButtonText: this.translateService.instant('general.close'),
        confirmButtonType: 'default'
      }
    });
  }
}
