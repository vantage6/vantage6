import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { getLazyProperties } from '../helpers/api.helper';
import { BaseStudy, Study, StudyLazyProperties, StudyCreate, StudyEdit, GetStudyParameters } from '../models/api/study.model';
import { Pagination } from '../models/api/pagination.model';

@Injectable({
  providedIn: 'root'
})
export class StudyService {
  constructor(private apiService: ApiService) {}

  async getStudies(params: GetStudyParameters | null = null): Promise<BaseStudy[]> {
    const result = await this.apiService.getForApi<Pagination<BaseStudy>>('/study', { ...params, per_page: 9999 });
    return result.data;
  }

  async getStudy(studyID: string, lazyProperties: StudyLazyProperties[] = [], params: GetStudyParameters | null = null): Promise<Study> {
    const study = await this.apiService.getForApi<Study>(`/study/${studyID}`, params);

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
