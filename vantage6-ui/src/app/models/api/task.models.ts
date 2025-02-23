import { BaseLink } from './base.model';
import { BaseOrganization } from './organization.model';
import { BaseUser } from './user.model';
import { NodeStatus } from './node.model';

export enum TaskLazyProperties {
  InitOrg = 'init_org',
  InitUser = 'init_user',
  Runs = 'runs'
}

export enum TaskSortProperties {
  ID = 'id',
  Name = 'name'
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
  Killed = 'killed by user'
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
}

export interface BaseTask {
  id: number;
  name: string;
  description: string;
  status: TaskStatus;
  session: BaseLink;
  image: string;
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
  input?: TaskInput;
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
  parameters?: string;
}

export interface TaskRun {
  id: number;
  status: TaskStatus;
  input: string;
  node: RunNode;
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

interface TaskInput {
  method: string;
  parameters: TaskParameter[];
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

export interface TaskDatabase {
  label: string;
  query?: string;
  sheet_name?: string;
}

export interface CreateTask {
  name: string;
  description: string;
  image: string;
  session_id: number;
  collaboration_id: number;
  study_id?: number;
  store_id: number;
  server_url: string;
  databases: TaskDatabase[];
  organizations: CreateTaskOrganization[];
}

export interface KillTask {
  id: number;
}

export interface CreateTaskOrganization {
  id: number;
  input: string;
}

export interface CreateTaskInput {
  method: string;
  kwargs: object;
}

export interface ColumnRetrievalInput {
  collaboration_id: number;
  db_label: string;
  organizations: CreateTaskOrganization[];
  query?: string;
  sheet_name?: string;
}

// The result of the /column endpoint is either a task or a list of column names
export interface ColumnRetrievalResult extends BaseTask {
  columns?: string[];
}
