import { Injectable } from '@angular/core';
import { Collaboration } from '../models/api/Collaboration.model';
import { ApiService } from './api.service';
import { Pagination } from '../models/api/pagination.model';
import { environment } from 'src/environments/environment';

@Injectable({
  providedIn: 'root'
})
export class CollaborationService {
  constructor(private apiService: ApiService) {}

  async getCollaborations(): Promise<Collaboration[]> {
    const result = await this.apiService.get<Pagination<Collaboration>>(environment.api_url + '/collaboration');
    return result.data;
  }

  async getCollaboration(id: string): Promise<Collaboration> {
    const result = await this.apiService.get<Collaboration>(environment.api_url + `/collaboration/${id}`);
    return result;
  }
}
