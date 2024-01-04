export interface AlgorithmStore {
  id: number;
  name: string;
  url: string;
  collaborations: string;
}

export interface AlgorithmStoreForm {
  name: string;
  algorithm_store_url: string;
  server_url: string;
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
