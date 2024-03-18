import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Pagination } from '../models/api/pagination.model';
import {
  BaseCollaboration,
  Collaboration,
  CollaborationCreate,
  CollaborationLazyProperties,
  GetCollaborationParameters
} from '../models/api/collaboration.model';
import { getLazyProperties } from '../helpers/api.helper';
import { PermissionService } from './permission.service';
import { OperationType, ResourceType, ScopeType } from '../models/api/rule.model';
import { StudyService } from './study.service';

@Injectable({
  providedIn: 'root'
})
export class CollaborationService {
  constructor(
    private apiService: ApiService,
    private permissionService: PermissionService,
    private studyService: StudyService
  ) {}

  async getCollaborations(parameters?: GetCollaborationParameters): Promise<BaseCollaboration[]> {
    //TODO: Add backend no pagination instead of page size 9999
    const result = await this.apiService.getForApi<Pagination<BaseCollaboration>>('/collaboration', { ...parameters, per_page: 9999 });
    return result.data;
  }

  async getPaginatedCollaborations(currentPage: number, parameters?: GetCollaborationParameters): Promise<Pagination<BaseCollaboration>> {
    const result = await this.apiService.getForApiWithPagination<BaseCollaboration>(`/collaboration`, currentPage, parameters);
    return result;
  }

  async getCollaboration(collaborationID: string, lazyProperties: CollaborationLazyProperties[] = []): Promise<Collaboration> {
    const result = await this.apiService.getForApi<BaseCollaboration>(`/collaboration/${collaborationID}`);

    const collaboration: Collaboration = { ...result, organizations: [], nodes: [], tasks: [], algorithm_stores: [], studies: [] };
    await getLazyProperties(result, collaboration, lazyProperties, this.apiService);

    return collaboration;
  }

  async createCollaboration(collaboration: CollaborationCreate): Promise<BaseCollaboration> {
    return await this.apiService.postForApi<BaseCollaboration>(`/collaboration`, collaboration);
  }

  async editCollaboration(collaborationID: string, collaboration: CollaborationCreate): Promise<BaseCollaboration> {
    return await this.apiService.patchForApi<BaseCollaboration>(`/collaboration/${collaborationID}`, collaboration);
  }

  async deleteCollaboration(collaborationID: string): Promise<void> {
    return await this.apiService.deleteForApi(`/collaboration/${collaborationID}?delete_dependents=true`);
  }
}
