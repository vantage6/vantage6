import { Injectable } from '@angular/core';
import { CHOSEN_COLLABORATION } from '../models/constants/sessionStorage';
import { BehaviorSubject } from 'rxjs';
import { CollaborationService } from './collaboration.service';
import { Collaboration, CollaborationLazyProperties } from '../models/api/collaboration.model';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class ChosenCollaborationService {
  isInitialized$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);
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

  private async initData() {
    const collaborationIDFromSession = sessionStorage.getItem(CHOSEN_COLLABORATION);
    if (collaborationIDFromSession) {
      const collaboration = await this.getCollaboration(collaborationIDFromSession);
      this.collaboration$.next(collaboration);
    }
    this.isInitialized$.next(true);
  }

  private async getCollaboration(id: string): Promise<Collaboration> {
    return await this.collaborationService.getCollaboration(id, [CollaborationLazyProperties.Organizations]);
  }
}
