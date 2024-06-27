import { Injectable } from '@angular/core';
import { ReviewCreate, StoreReview } from '../models/api/review.model';
import { ApiService } from './api.service';
import { Pagination } from '../models/api/pagination.model';

@Injectable({
  providedIn: 'root'
})
export class StoreReviewService {
  constructor(private apiService: ApiService) {}

  async getReviews(store_url: string, params: object = {}): Promise<StoreReview[]> {
    const result = await this.apiService.getForAlgorithmApi<Pagination<StoreReview>>(store_url, `/api/review`, {
      ...params,
      per_page: 9999
    });
    return result.data;
  }

  async getReview(store_url: string, review_id: string): Promise<StoreReview> {
    return await this.apiService.getForAlgorithmApi<StoreReview>(store_url, `/api/review/${review_id}`);
  }

  async createReview(store_url: string, review: ReviewCreate): Promise<StoreReview> {
    return await this.apiService.postForAlgorithmApi<StoreReview>(store_url, `/api/review`, review);
  }

  async approveReview(store_url: string, review_id: number, comment: string): Promise<StoreReview> {
    return await this.apiService.postForAlgorithmApi<StoreReview>(store_url, `/api/review/${review_id}/approve`, { comment: comment });
  }

  async rejectReview(store_url: string, review_id: number, comment: string): Promise<StoreReview> {
    return await this.apiService.postForAlgorithmApi<StoreReview>(store_url, `/api/review/${review_id}/reject`, { comment: comment });
  }

  async deleteReview(store_url: string, review_id: number): Promise<void> {
    await this.apiService.deleteForAlgorithmApi(store_url, `/api/review/${review_id}`);
  }
}
