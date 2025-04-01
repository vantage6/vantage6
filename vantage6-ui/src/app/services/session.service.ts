import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import {
  BaseSession,
  CreateDataframe,
  CreateSession,
  Dataframe,
  DataframePreprocess,
  GetDataframeParameters,
  GetSessionParameters,
  Session,
  SessionLazyProperties
} from 'src/app/models/api/session.models';
import { Pagination } from 'src/app/models/api/pagination.model';
import { getLazyProperties } from 'src/app/helpers/api.helper';

@Injectable({
  providedIn: 'root'
})
export class SessionService {
  constructor(private apiService: ApiService) {}

  async getSessions(parameters?: GetSessionParameters): Promise<BaseSession[]> {
    const result = await this.apiService.getForApi<Pagination<BaseSession>>('/session', { ...parameters, per_page: 9999 });
    return result.data;
  }

  async getPaginatedSessions(currentPage: number, parameters?: GetSessionParameters): Promise<Pagination<BaseSession>> {
    const result = await this.apiService.getForApiWithPagination<BaseSession>(`/session`, currentPage, parameters);
    return result;
  }

  async getSession(id: number, lazyProperties: SessionLazyProperties[] = []): Promise<Session> {
    const result = await this.apiService.getForApi<BaseSession>(`/session/${id}`);
    const session: Session = { ...result, owner: undefined };
    await getLazyProperties(result, session, lazyProperties, this.apiService);
    return session;
  }

  async getDataframes(sessionId: number): Promise<Dataframe[]> {
    const result = await this.apiService.getForApi<Pagination<Dataframe>>(`/session/${sessionId}/dataframe`, { per_page: 9999 });
    return result.data;
  }

  async getPaginatedDataframes(
    sessionId: number,
    currentPage: number,
    parameters?: GetDataframeParameters
  ): Promise<Pagination<Dataframe>> {
    return await this.apiService.getForApiWithPagination<any>(`/session/${sessionId}/dataframe`, currentPage, parameters);
  }

  async getDataframe(dataframeID: number): Promise<Dataframe> {
    return await this.apiService.getForApi<Dataframe>(`/session/dataframe/${dataframeID}`);
  }

  async createSession(createSession: CreateSession): Promise<BaseSession> {
    return await this.apiService.postForApi<BaseSession>('/session', createSession);
  }

  async createDataframe(sessionId: number, createDataframe: CreateDataframe): Promise<Dataframe> {
    return await this.apiService.postForApi<any>(`/session/${sessionId}/dataframe`, createDataframe);
  }

  async createPreprocessingTask(dataframeId: number, preprocessTask: DataframePreprocess): Promise<Dataframe> {
    return await this.apiService.postForApi<Dataframe>(`/session/dataframe/${dataframeId}/preprocess`, preprocessTask);
  }

  async editSession(sessionId: string, newValue: any): Promise<Session> {
    return await this.apiService.patchForApi<Session>(`/session/${sessionId}`, newValue);
  }

  async deleteSession(id: number): Promise<void> {
    return await this.apiService.deleteForApi(`/session/${id}`);
  }

  async deleteDataframe(dataframeID: number): Promise<void> {
    return await this.apiService.deleteForApi(`/session/dataframe/${dataframeID}`);
  }
}
