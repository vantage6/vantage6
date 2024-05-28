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
  server_url: string;
  collaboration_id?: string;
  force?: boolean;
}

export interface EditAlgorithmStore {
  name: string;
}

export enum AlgorithmStoreLazyProperties {
  Collaborations = 'collaborations'
}

export interface StorePolicy {
  key: string;
  value: string;
}

export enum AvailableStorePolicies {
  ALGORITHM_VIEW = 'algorithm_view',
  ALLOWED_SERVERS = 'allowed_servers',
  ALLOWED_SERVERS_EDIT = 'allowed_servers_edit',
  ALLOW_LOCALHOST = 'allow_localhost'
}

export enum DefaultStorePolicies {
  ALGORITHM_VIEW = 'public',
  ALLOWED_SERVERS = 'All',
  ALLOWED_SERVERS_EDIT = 'All',
  ALLOW_LOCALHOST = 'false'
}
