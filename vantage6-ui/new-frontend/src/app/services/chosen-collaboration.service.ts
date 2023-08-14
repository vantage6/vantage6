import { Injectable } from '@angular/core';
import { CHOSEN_COLLABORATION } from '../models/constants/sessionStorage';
import { BehaviorSubject } from 'rxjs';
import { CollaborationService } from './collaboration.service';
import { Collaboration, CollaborationLazyProperties } from '../models/api/Collaboration.model';

@Injectable({
  providedIn: 'root'
})
export class ChosenCollaborationService {
  collaboration$: BehaviorSubject<Collaboration | null> = new BehaviorSubject<Collaboration | null>(null);

  constructor(private collaborationService: CollaborationService) {
    this.initData();
  }

  async setCollaboration(id: string) {
    sessionStorage.setItem(CHOSEN_COLLABORATION, id);
    const collaboration = await this.collaborationService.getCollaboration(id, [CollaborationLazyProperties.Organizations]);
    this.collaboration$.next(collaboration);
  }

  private async initData() {
    const collaborationIDFromSession = sessionStorage.getItem(CHOSEN_COLLABORATION);
    if (collaborationIDFromSession) {
      const collaboration = await this.collaborationService.getCollaboration(collaborationIDFromSession, [
        CollaborationLazyProperties.Organizations
      ]);
      this.collaboration$.next(collaboration);
    }
  }
}
