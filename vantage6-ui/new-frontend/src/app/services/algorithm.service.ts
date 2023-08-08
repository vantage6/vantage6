import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { environment } from 'src/environments/environment';
import { Pagination } from '../models/api/pagination.model';
import { Algorithm } from '../models/api/algorithm.model';

@Injectable({
  providedIn: 'root'
})
export class AlgorithmService {
  constructor(private apiService: ApiService) {}

  async getAlgorithms(): Promise<Algorithm[]> {
    const result = await this.apiService.get<Pagination<Algorithm>>(`${environment.algorithm_server_url}/algorithm`);
    return result.data;
  }
}
