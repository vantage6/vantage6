import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Pagination } from '../models/api/pagination.model';
import {
  BaseCollaboration,
  Collaboration,
  CollaborationCreate,
  CollaborationLazyProperties,
  CollaborationSortProperties
} from '../models/api/collaboration.model';

@Injectable({
  providedIn: 'root'
})
export class CollaborationService {
  constructor(private apiService: ApiService) {}

  async getCollaborations(sortProperty: CollaborationSortProperties = CollaborationSortProperties.ID): Promise<BaseCollaboration[]> {
    const result = await this.apiService.getForApi<Pagination<BaseCollaboration>>('/collaboration', {
      //TODO: Sorting causes backend error
      //sort: sortProperty
    });
    return result.data;
  }

  async getPaginatedCollaborations(
    currentPage: number,
    sortProperty: CollaborationSortProperties = CollaborationSortProperties.ID
  ): Promise<Pagination<BaseCollaboration>> {
    const result = await this.apiService.getForApiWithPagination<BaseCollaboration>(`/collaboration`, currentPage, {
      //TODO: Sorting causes backend error
      //sort: sortProperty
    });
    return result;
  }

  async getCollaboration(collaborationID: string, lazyProperties: CollaborationLazyProperties[] = []): Promise<Collaboration> {
    const result = await this.apiService.getForApi<BaseCollaboration>(`/collaboration/${collaborationID}`);

    const collaboration: Collaboration = { ...result, organizations: [], nodes: [], tasks: [] };

    await Promise.all(
      lazyProperties.map(async (lazyProperty) => {
        if (!result[lazyProperty]) return;

        const resultProperty = await this.apiService.getForApi<Pagination<any>>(result[lazyProperty]);
        collaboration[lazyProperty] = resultProperty.data;
      })
    );

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
