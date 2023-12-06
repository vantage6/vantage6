import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Pagination } from '../models/api/pagination.model';
import { Algorithm, BaseAlgorithm } from '../models/api/algorithm.model';

@Injectable({
  providedIn: 'root'
})
export class AlgorithmService {
  constructor(private apiService: ApiService) {}

  async getAlgorithms(): Promise<BaseAlgorithm[]> {
    const result = await this.apiService.getForAlgorithmApi<Pagination<Algorithm>>('/algorithm');
    return result.data;
  }

  async getAlgorithm(id: string): Promise<Algorithm> {
    const result = await this.apiService.getForAlgorithmApi<Algorithm>(`/algorithm/${id}`);
    return result;
  }

  async getAlgorithmByUrl(url: string): Promise<Algorithm> {
    const result = await this.apiService.getForAlgorithmApi<Algorithm>(`/algorithm/${encodeURIComponent(url)}`);
    return result;
  }
}
