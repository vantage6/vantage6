export interface NodeOnlineStatusMsg {
  id: number;
  name: string;
  online: boolean;
}

export interface AlgorithmStatusChangeMsg {
  status: string;
  collaboration_id: number;
  task_id: number;
  job_id: number;
  run_id: number;
  node_id: number;
  organization_id: number;
  parent_id: number;
}
