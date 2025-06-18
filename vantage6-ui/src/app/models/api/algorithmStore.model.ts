import { BaseCollaboration } from './collaboration.model';

export interface BaseAlgorithmStore {
  id: number;
  name: string;
  url: string;
  collaborations: string;
}

export interface AlgorithmStore {
  id: number;
  name: string;
  url: string;
  collaborations: BaseCollaboration[];
  all_collaborations: boolean;
}

export interface AlgorithmStoreForm {
  name: string;
  algorithm_store_url: string;
  all_collaborations: boolean;
  collaboration_id?: string;
}

export interface AddAlgorithmStore {
  name: string;
  algorithm_store_url: string;
  collaboration_id?: string;
}

export interface EditAlgorithmStore {
  name: string;
}

export enum AlgorithmStoreLazyProperties {
  Collaborations = 'collaborations'
}

export enum AvailableStorePolicies {
  ALGORITHM_VIEW = 'algorithm_view',
  MIN_REVIEWERS = 'min_reviewers',
  ASSIGN_REVIEW_OWN_ALGORITHM = 'assign_review_own_algorithm',
  MIN_REVIEWING_ORGANIZATIONS = 'min_reviewing_organizations',
  ALLOWED_REVIEWERS = 'allowed_reviewers',
  ALLOWED_REVIEW_ASSIGNERS = 'allowed_review_assigners'
}
export interface StorePolicies {
  // TODO it would be nice if we could have a more specific type here like
  // { algorithm_view: string, allowed_servers: string[], allow_localhost: boolean }
  // but that doesn't work with conversion to table in the algorithmStoreReadComponent
  [key: string]: string | string[] | boolean;
}

export enum AlgorithmViewPolicies {
  PUBLIC = 'public',
  WHITELISTED = 'whitelisted',
  PRIVATE = 'private'
}
