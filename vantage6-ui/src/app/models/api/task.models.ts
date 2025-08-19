import { BaseLink } from './base.model';
import { BaseOrganization } from './organization.model';
import { BaseUser } from './user.model';
import { NodeStatus } from './node.model';
import { AlgorithmStepType } from './session.models';

export enum TaskLazyProperties {
  InitOrg = 'init_org',
  InitUser = 'init_user',
  Runs = 'runs'
}

export enum TaskSortProperties {
  ID = 'id',
  IDDesc = '-id',
  Name = 'name'
}

export enum TaskDatabaseType {
  Dataframe = 'dataframe',
  Source = 'source'
}

export enum TaskStatus {
  Pending = 'pending',
  Initializing = 'initializing',
  Active = 'active',
  Completed = 'completed',
  Failed = 'failed',
  StartFailed = 'start failed',
  NoDockerImage = 'non-existing Docker image',
  NotAllowed = 'not allowed',
  Crashed = 'crashed',
  Killed = 'killed by user',
  Unknown = 'unknown error'
}

export enum TaskStatusGroup {
  Pending = 'pending',
  Active = 'active',
  Success = 'success',
  Error = 'error'
}

export interface GetTaskParameters {
  collaboration_id?: string;
  name?: string;
  init_user_id?: string;
  sort?: TaskSortProperties;
  parent_id?: number;
  include?: string;
  is_user_created?: number;
  status?: TaskStatus;
  dataframe_id?: number;
}

export interface BaseTask {
  id: number;
  name: string;
  description: string;
  status: TaskStatus;
  session: BaseLink;
  image: string;
  method: string;
  action: AlgorithmStepType;
  arguments: TaskParameter[];
  init_org: BaseLink;
  init_user: BaseLink;
  algorithm_store?: BaseLink;
  runs: TaskRun[];
  created_at: string;
  databases: TaskDBOutput[];
  parent?: BaseLink;
  study?: BaseLink;
  collaboration?: BaseLink;
}

export interface Task {
  id: number;
  name: string;
  description: string;
  status: TaskStatus;
  session: BaseLink;
  image: string;
  method: string;
  action: AlgorithmStepType;
  arguments: TaskParameter[];
  init_org?: BaseOrganization;
  init_user?: BaseUser;
  runs: TaskRun[];
  results?: TaskResult[];
  created_at: string;
  databases: TaskDBOutput[];
  parent?: BaseLink;
  study?: BaseLink;
  collaboration?: BaseLink;
  algorithm_store?: BaseLink;
}

export interface TaskDBOutput {
  label: string;
  position: number;
  dataframe_id?: number;
  dataframe_name?: string;
  type: TaskDatabaseType;
}

export interface TaskRun {
  id: number;
  status: TaskStatus;
  arguments: string;
  node: RunNode;
  action: AlgorithmStepType;
  assigned_at: string;
  started_at?: string;
  finished_at?: string;
  log?: string;
  organization?: BaseLink;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  result?: any;
}

//Not compatible with BaseNode
export interface RunNode {
  id: number;
  name: string;
  status?: NodeStatus | null;
}

export interface TaskParameter {
  label: string;
  value: string;
}

export interface TaskResult {
  id: number;
  result?: string;
  decoded_result?: object;
}

interface CreateTaskDatabase {
  label?: string;
  dataframe_id?: number;
  type: TaskDatabaseType;
  multiple?: boolean;
}

export interface CreateTask {
  name: string;
  description: string;
  image: string;
  method: string;
  session_id: number;
  collaboration_id: number;
  study_id?: number;
  store_id: number;
  organizations: CreateTaskOrganization[];
  databases: CreateTaskDatabase[][];
}

export interface KillTask {
  id: number;
}

export interface CreateTaskOrganization {
  id: number;
  arguments: string;
}
