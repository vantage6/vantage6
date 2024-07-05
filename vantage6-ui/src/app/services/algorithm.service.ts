import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Algorithm, AlgorithmForm } from 'src/app/models/api/algorithm.model';
import { ChosenCollaborationService } from './chosen-collaboration.service';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { Pagination } from 'src/app/models/api/pagination.model';
import { ChosenStoreService } from './chosen-store.service';

@Injectable({
  providedIn: 'root'
})
export class AlgorithmService {
  constructor(
    private apiService: ApiService,
    private chosenCollaborationService: ChosenCollaborationService,
    private chosenStoreService: ChosenStoreService
  ) {}

  async getAlgorithms(params: object = {}): Promise<Algorithm[]> {
    const algorithmStores = this.getAlgorithmStoresForCollaboration();
    const results = await Promise.all(
      algorithmStores.map(async (algorithmStore) => {
        return await this.getAlgorithmsForAlgorithmStore(algorithmStore, params);
      })
    );
    // combine the list of lists of algorithms
    return results.reduce((accumulator, val) => accumulator.concat(val), []);
  }

  async getAlgorithmsForAlgorithmStore(algorithmStore: AlgorithmStore, params: object = {}): Promise<Algorithm[]> {
    const result = await this.apiService.getForAlgorithmApi<Pagination<Algorithm>>(`${algorithmStore.url}/api`, '/algorithm', {
      per_page: 9999,
      ...params
    });
    const algorithms = result.data;
    // set algorithm store url for each algorithm
    algorithms.forEach((algorithm) => {
      algorithm.algorithm_store_url = algorithmStore.url;
      algorithm.algorith_store_id = algorithmStore.id;
    });
    return algorithms;
  }

  async getAlgorithm(algorithm_store_url: string, id: string): Promise<Algorithm> {
    const result = await this.apiService.getForAlgorithmApi<Algorithm>(algorithm_store_url, `/api/algorithm/${id}`);
    return result;
  }

  async getAlgorithmByUrl(url: string): Promise<Algorithm | null> {
    const result = await this.getAlgorithms({ image: url });
    if (result.length === 0) {
      return null;
    }
    return result[0];
  }

  async createAlgorithm(algorithm: AlgorithmForm): Promise<Algorithm | undefined> {
    const algorithmStore = this.chosenStoreService.store$.value;
    if (!algorithmStore) return;
    const result = await this.apiService.postForAlgorithmApi<Algorithm>(algorithmStore.url, '/api/algorithm', algorithm);
    return result;
  }

  async editAlgorithm(algorithmId: string, algorithm: AlgorithmForm): Promise<Algorithm | undefined> {
    const algorithmStore = this.chosenStoreService.store$.value;
    if (!algorithmStore) return;
    const result = await this.apiService.patchForAlgorithmApi<Algorithm>(algorithmStore.url, `/api/algorithm/${algorithmId}`, algorithm);
    return result;
  }

  async deleteAlgorithm(algorithmId: string): Promise<void> {
    const algorithmStore = this.chosenStoreService.store$.value;
    if (!algorithmStore) return;
    return await this.apiService.deleteForAlgorithmApi(algorithmStore.url, `/api/algorithm/${algorithmId}`);
  }

  private getAlgorithmStoresForCollaboration(): AlgorithmStore[] {
    const collaboration = this.chosenCollaborationService.collaboration$.getValue();
    if (!collaboration) {
      return [];
    }
    return collaboration.algorithm_stores;
  }
}
