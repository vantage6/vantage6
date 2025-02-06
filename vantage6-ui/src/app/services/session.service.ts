import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import {
  BaseSession,
  ColumnRetrievalInput,
  ColumnRetrievalResult,
  CreateSession,
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
    const session: Session = { ...result, init_org: undefined, init_user: undefined };
    await getLazyProperties(result, session, lazyProperties, this.apiService);
    return session;
  }

  async createSession(createSession: CreateSession): Promise<BaseSession> {
    return await this.apiService.postForApi<BaseSession>('/session', createSession);
  }

  async deleteSession(id: number): Promise<void> {
    return await this.apiService.deleteForApi(`/session/${id}`);
  }

  async getColumnNames(columnRetrieve: ColumnRetrievalInput): Promise<ColumnRetrievalResult> {
    return await this.apiService.postForApi<ColumnRetrievalResult>(`/column`, columnRetrieve);
  }
}
