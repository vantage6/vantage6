import { Injectable } from '@angular/core';
import { CHOSEN_COLLABORATION } from '../models/constants/sessionStorage';
import { BehaviorSubject } from 'rxjs';
import { CollaborationService } from './collaboration.service';
import { Collaboration, CollaborationLazyProperties } from '../models/api/collaboration.model';
import { getLazyProperties } from '../helpers/api.helper';
import { StudyLazyProperties } from '../models/api/study.model';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class ChosenCollaborationService {
  id: string = '';
  isInitialized$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);
  collaboration$: BehaviorSubject<Collaboration | null> = new BehaviorSubject<Collaboration | null>(null);

  constructor(
    private collaborationService: CollaborationService,
    private apiService: ApiService
  ) {
    this.initData();
  }

  async setCollaboration(id: string) {
    this.id = id;
    sessionStorage.setItem(CHOSEN_COLLABORATION, id);
    const collaboration = await this.getCollaboration(id);
    this.collaboration$.next(collaboration);
  }

  async refresh(refresh_id: string | null = null) {
    // only refresh if the updated collaboration is the same as the chosen one
    // if refresh_id is null, refresh anyway (e.g. when algorithm store is added that
    // is part of all collaborations)
    if (this.id && (!refresh_id || this.id === refresh_id)) {
      await this.setCollaboration(this.id);
    }
  }

  private async initData() {
    const collaborationIDFromSession = sessionStorage.getItem(CHOSEN_COLLABORATION);
    if (collaborationIDFromSession) {
      this.id = collaborationIDFromSession;
      const collaboration = await this.getCollaboration(this.id);
      this.collaboration$.next(collaboration);
    }
    this.isInitialized$.next(true);
  }

  private async getCollaboration(id: string): Promise<Collaboration> {
    const collab = await this.collaborationService.getCollaboration(id, [
      CollaborationLazyProperties.Organizations,
      CollaborationLazyProperties.AlgorithmStores,
      CollaborationLazyProperties.Studies
    ]);
    // set the organizations within the studies
    if (collab.studies) {
      for (const study of collab.studies) {
        await getLazyProperties(study, study, [StudyLazyProperties.Organizations], this.apiService);
      }
    }

    return collab;
  }
}
