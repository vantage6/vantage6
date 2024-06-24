import { Injectable } from '@angular/core';
import { ReviewCreate, StoreReview } from '../models/api/review.model';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class StoreReviewService {
  constructor(private apiService: ApiService) {}

  async createReview(store_url: string, review: ReviewCreate): Promise<StoreReview> {
    return await this.apiService.postForAlgorithmApi<StoreReview>(store_url, `/api/review`, review);
  }
}
