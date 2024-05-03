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
