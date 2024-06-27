import { StoreUser } from './store-user.model';

export enum ReviewStatus {
  AwaitingReviewerAssignment = 'awaiting reviewer assignment',
  UnderReview = 'under review',
  Approved = 'approved',
  Rejected = 'rejected',
  Replaced = 'replaced'
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
}

export interface ReviewForm {
  approve: boolean;
  comment?: string;
}
