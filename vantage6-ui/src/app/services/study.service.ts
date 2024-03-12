import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { getLazyProperties } from '../helpers/api.helper';
import { BaseStudy, Study, StudyLazyProperties, StudyCreate, StudyEdit } from '../models/api/study.model';

@Injectable({
  providedIn: 'root'
})
export class StudyService {
  constructor(private apiService: ApiService) {}

  async getStudy(studyID: string, lazyProperties: StudyLazyProperties[] = []): Promise<Study> {
    const study = await this.apiService.getForApi<Study>(`/study/${studyID}`);

    await getLazyProperties(study, study, lazyProperties, this.apiService);

    return study;
  }

  async createStudy(study: StudyCreate): Promise<BaseStudy> {
    return await this.apiService.postForApi<BaseStudy>('/study', study);
  }

  async editStudy(studyID: string, study: StudyEdit): Promise<Study> {
    return await this.apiService.patchForApi<Study>(`/study/${studyID}`, study);
  }

  async deleteStudy(studyID: string): Promise<void> {
    return await this.apiService.deleteForApi(`/study/${studyID}?delete_dependents=true`);
  }
}
