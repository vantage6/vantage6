import { Injectable } from '@angular/core';
import { GetStoreReviewParameters, ReviewCreate, StoreReview } from '../models/api/review.model';
import { ApiService } from './api.service';
import { Pagination } from '../models/api/pagination.model';
import { AlgorithmStore } from '../models/api/algorithmStore.model';

@Injectable({
  providedIn: 'root'
})
export class StoreReviewService {
  constructor(private apiService: ApiService) {}

  async getReviews(algoStore: AlgorithmStore, params: object = {}): Promise<StoreReview[]> {
    const result = await this.apiService.getForAlgorithmApi<Pagination<StoreReview>>(algoStore, `/review`, {
      ...params,
      per_page: 9999
    });
    return result.data;
  }

  async getPaginatedReviews(
    algoStore: AlgorithmStore,
    currentPage: number,
    parameters?: GetStoreReviewParameters
  ): Promise<Pagination<StoreReview>> {
    return await this.apiService.getForAlgorithmApiWithPagination<StoreReview>(algoStore, `/review`, currentPage, {
      ...parameters
    });
  }

  async getReview(algoStore: AlgorithmStore, review_id: string): Promise<StoreReview> {
    return await this.apiService.getForAlgorithmApi<StoreReview>(algoStore, `/review/${review_id}`);
  }

  async createReview(algoStore: AlgorithmStore, review: ReviewCreate): Promise<StoreReview> {
    return await this.apiService.postForAlgorithmApi<StoreReview>(algoStore, `/review`, review);
  }

  async approveReview(algoStore: AlgorithmStore, review_id: number, comment: string): Promise<StoreReview> {
    return await this.apiService.postForAlgorithmApi<StoreReview>(algoStore, `/review/${review_id}/approve`, { comment: comment });
  }

  async rejectReview(algoStore: AlgorithmStore, review_id: number, comment: string): Promise<StoreReview> {
    return await this.apiService.postForAlgorithmApi<StoreReview>(algoStore, `/review/${review_id}/reject`, { comment: comment });
  }

  async deleteReview(algoStore: AlgorithmStore, review_id: number): Promise<void> {
    await this.apiService.deleteForAlgorithmApi(algoStore, `/review/${review_id}`);
  }
}
