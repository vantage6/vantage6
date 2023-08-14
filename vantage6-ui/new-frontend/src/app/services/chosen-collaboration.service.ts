import { Injectable } from '@angular/core';
import { CHOSEN_COLLABORATION } from '../models/constants/sessionStorage';
import { BehaviorSubject } from 'rxjs';
import { CollaborationService } from './collaboration.service';
import { Collaboration } from '../models/api/Collaboration.model';

@Injectable({
  providedIn: 'root'
})
export class ChosenCollaborationService {
  collaboration$: BehaviorSubject<Collaboration | null> = new BehaviorSubject<Collaboration | null>(null);

  constructor(private collaborationService: CollaborationService) {
    this.initData();
  }

  setCollaboration(collaboration: Collaboration) {
    sessionStorage.setItem(CHOSEN_COLLABORATION, collaboration.id.toString());
    this.collaboration$.next(collaboration);
  }

  private async initData() {
    const collaborationIDFromSession = sessionStorage.getItem(CHOSEN_COLLABORATION);
    if (collaborationIDFromSession) {
      const collaboration = await this.collaborationService.getCollaboration(collaborationIDFromSession);
      this.collaboration$.next(collaboration);
    }
  }
}
