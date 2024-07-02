import { Algorithm } from './algorithm.model';
import { StoreUser } from './store-user.model';

export enum ReviewLazyProperties {
  Algorithm = 'algorithm'
}

export enum ReviewStatus {
  AwaitingReviewerAssignment = 'awaiting reviewer assignment',
  UnderReview = 'under review',
  Approved = 'approved',
  Rejected = 'rejected',
  Dropped = 'dropped'
}

export interface ReviewCreate {
  algorithm_id: number;
  reviewer_id: number;
}

export interface StoreReview {
  id: number;
  status: ReviewStatus;
  algorithm_id: number;
  reviewer: StoreUser;
  comment?: string;
  algorithm?: Algorithm;
}

export interface ReviewForm {
  approve: boolean;
  comment?: string;
}

export interface GetStoreReviewParameters {
  reviewer_id?: number;
  algorithm_id?: number;
  under_review?: boolean;
  approved?: boolean;
  rejected?: boolean;
  reviewed?: boolean;
  awaiting_reviewer_assignment?: boolean;
}
