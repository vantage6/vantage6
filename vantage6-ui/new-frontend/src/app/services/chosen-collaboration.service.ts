import { Injectable } from '@angular/core';
import { CHOSEN_COLLABORATION } from '../models/constants/sessionStorage';
import { BehaviorSubject } from 'rxjs';
import { CollaborationService } from './collaboration.service';
import { Collaboration, CollaborationLazyProperties } from '../models/api/collaboration.model';
import { BaseNode } from '../models/api/node.model';
import { ApiService } from './api.service';
import { Pagination } from '../models/api/pagination.model';

@Injectable({
  providedIn: 'root'
})
export class ChosenCollaborationService {
  collaboration$: BehaviorSubject<Collaboration | null> = new BehaviorSubject<Collaboration | null>(null);

  constructor(
    private collaborationService: CollaborationService,
    private apiService: ApiService
  ) {
    this.initData();
  }

  async setCollaboration(id: string) {
    sessionStorage.setItem(CHOSEN_COLLABORATION, id);
    const collaboration = await this.getCollaboration(id);
    this.collaboration$.next(collaboration);
  }

  //TODO: Should be in node service
  async getNodes(): Promise<BaseNode[]> {
    const result = await this.apiService.getForApi<Pagination<BaseNode>>(`/node?collaboration_id=${this.collaboration$.value?.id}`);

    //TODO: Remove mock data!
    result.data.forEach((node) => {
      node.config = [
        { key: 'database_labels', value: 'default' },
        { key: 'db_type_default', value: 'sql' },
        { key: 'database_labels', value: 'example' },
        { key: 'db_type_example', value: 'excel' }
      ];
    });

    return result.data;
  }

  private async initData() {
    const collaborationIDFromSession = sessionStorage.getItem(CHOSEN_COLLABORATION);
    if (collaborationIDFromSession) {
      const collaboration = await this.getCollaboration(collaborationIDFromSession);
      this.collaboration$.next(collaboration);
    }
  }

  private async getCollaboration(id: string): Promise<Collaboration> {
    return await this.collaborationService.getCollaboration(id, [CollaborationLazyProperties.Organizations]);
  }
}
