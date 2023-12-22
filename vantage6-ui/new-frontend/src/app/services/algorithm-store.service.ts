import { Injectable } from '@angular/core';
import { AddAlgorithmStore } from '../models/api/algorithmStore.model';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class AlgorithmStoreService {
  constructor(private apiService: ApiService) {}

  async addAlgorithmStore(addAlgorithmStore: AddAlgorithmStore): Promise<void> {
    return await this.apiService.postForApi<void>(`/algorithmstore`, addAlgorithmStore);
  }
}
