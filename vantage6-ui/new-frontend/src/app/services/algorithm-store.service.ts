import { Injectable } from '@angular/core';
import { AddAlgorithmStore, AlgorithmStore, EditAlgorithmStore } from '../models/api/algorithmStore.model';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class AlgorithmStoreService {
  constructor(private apiService: ApiService) {}

  async addAlgorithmStore(addAlgorithmStore: AddAlgorithmStore): Promise<void> {
    return await this.apiService.postForApi<void>(`/algorithmstore`, addAlgorithmStore);
  }

  async edit(id: string, editAlgorithmStore: EditAlgorithmStore): Promise<AlgorithmStore> {
    return await this.apiService.patchForApi<AlgorithmStore>(`/algorithmstore/${id}`, editAlgorithmStore);
  }

  async delete(id: string): Promise<void> {
    return await this.apiService.deleteForApi(`/algorithmstore/${id}`);
  }
}
