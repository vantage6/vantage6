import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Algorithm } from '../models/api/algorithm.model';
import { ChosenCollaborationService } from './chosen-collaboration.service';
import { AlgorithmStore } from '../models/api/algorithmStore.model';

@Injectable({
  providedIn: 'root'
})
export class AlgorithmService {
  constructor(
    private apiService: ApiService,
    private chosenCollaborationService: ChosenCollaborationService
  ) {}

  async getAlgorithms(params: object = {}): Promise<Algorithm[]> {
    const algorithmStores = this.getAlgorithmStoresForCollaboration();
    const results = await Promise.all(
      algorithmStores.map(async (algorithmStore) => {
        const algorithms = await this.apiService.getForAlgorithmApi<Algorithm[]>(`${algorithmStore.url}/api`, '/algorithm', {
          per_page: 9999,
          ...params
        });
        // set algorithm store url for each algorithm
        algorithms.forEach((algorithm) => {
          algorithm.algorithm_store_url = algorithmStore.url;
        });
        return algorithms;
      })
    );
    // combine the list of lists of algorithms
    return results.reduce((accumulator, val) => accumulator.concat(val), []);
  }

  async getAlgorithm(algorithm_store_url: string, id: string): Promise<Algorithm> {
    const result = await this.apiService.getForAlgorithmApi<Algorithm>(algorithm_store_url, `/algorithm/${id}`);
    return result;
  }

  async getAlgorithmByUrl(url: string): Promise<Algorithm | null> {
    const result = await this.getAlgorithms({ image: encodeURIComponent(url) });
    if (result.length === 0) {
      return null;
    }
    return result[0];
  }

  private getAlgorithmStoresForCollaboration(): AlgorithmStore[] {
    const collaboration = this.chosenCollaborationService.collaboration$.getValue();
    if (!collaboration) {
      return [];
    }
    return collaboration.algorithm_stores;
  }
}
