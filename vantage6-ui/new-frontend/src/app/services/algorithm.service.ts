import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Algorithm } from '../models/api/algorithm.model';

@Injectable({
  providedIn: 'root'
})
export class AlgorithmService {
  constructor(private apiService: ApiService) {}

  async getAlgorithms(): Promise<Algorithm[]> {
    const result = await this.apiService.getForAlgorithmApi<Algorithm[]>('/algorithm', { per_page: 9999 });
    return result;
  }

  async getAlgorithm(id: string): Promise<Algorithm> {
    const result = await this.apiService.getForAlgorithmApi<Algorithm>(`/algorithm/${id}`);
    return result;
  }

  async getAlgorithmByUrl(url: string): Promise<Algorithm | null> {
    const result = await this.apiService.getForAlgorithmApi<Algorithm[]>(`/algorithm`, { image: encodeURIComponent(url) });
    if (result.length === 0) {
      return null;
    }
    return result[0];
  }
}
