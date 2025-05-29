import { Injectable } from '@angular/core';
import {
  AddAlgorithmStore,
  AlgorithmStore,
  AlgorithmStoreLazyProperties,
  BaseAlgorithmStore,
  EditAlgorithmStore,
  StorePolicies
} from 'src/app/models/api/algorithmStore.model';
import { ApiService } from './api.service';
import { environment } from 'src/environments/environment';
import { Pagination } from 'src/app/models/api/pagination.model';
import { getLazyProperties } from 'src/app/helpers/api.helper';

@Injectable({
  providedIn: 'root'
})
export class AlgorithmStoreService {
  constructor(private apiService: ApiService) {}

  async getAlgorithmStores(): Promise<BaseAlgorithmStore[]> {
    const result = await this.apiService.getForApi<Pagination<BaseAlgorithmStore>>(`/algorithmstore`, { per_page: 9999 });
    return result.data;
  }

  async getAlgorithmStore(id: string, lazyProperties: AlgorithmStoreLazyProperties[] = []): Promise<AlgorithmStore> {
    const result = await this.apiService.getForApi<AlgorithmStore>(`/algorithmstore/${id}`);

    const store: AlgorithmStore = { ...result, collaborations: [], all_collaborations: result.collaborations === null };
    if (!result.all_collaborations) {
      await getLazyProperties(result, store, lazyProperties, this.apiService);
    }

    return store;
  }

  async addAlgorithmStore(addAlgorithmStore: AddAlgorithmStore): Promise<void> {
    return await this.apiService.postForApi<void>(`/algorithmstore`, addAlgorithmStore);
  }

  async edit(id: string, editAlgorithmStore: EditAlgorithmStore): Promise<AlgorithmStore> {
    return await this.apiService.patchForApi<AlgorithmStore>(`/algorithmstore/${id}`, editAlgorithmStore);
  }

  async delete(id: string): Promise<void> {
    return await this.apiService.deleteForApi(`/algorithmstore/${id}`);
  }

  async getAlgorithmStorePolicies(store_url: string, public_: boolean = false): Promise<StorePolicies> {
    const endpoint = public_ ? '/policy/public' : '/policy';
    return await this.apiService.getForAlgorithmApi<StorePolicies>(store_url, endpoint);
  }
}
