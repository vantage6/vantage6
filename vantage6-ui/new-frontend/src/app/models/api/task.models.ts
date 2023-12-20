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
  Crashed = 'crashed',
  Killed = 'killed by user'
}

export interface GetTaskParameters {
  collaboration_id?: string;
  init_user_id?: string;
  sort?: TaskSortProperties;
  parent_id?: number;
  include?: string;
  is_user_created?: number;
}

export interface BaseTask {
  id: number;
  name: string;
  description: string;
  status: TaskStatus;
  image: string;
  init_org: BaseLink;
  init_user: BaseLink;
  runs: TaskRun[];
  created_at: string;
  databases: TaskDBOutput[];
  parent?: BaseLink;
}

export interface Task {
  id: number;
  name: string;
  description: string;
  status: TaskStatus;
  image: string;
  input?: TaskInput;
  init_org?: BaseOrganization;
  init_user?: BaseUser;
  runs: TaskRun[];
  results?: TaskResult[];
  created_at: string;
  databases: TaskDBOutput[];
  parent?: BaseLink;
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

interface TaskParameter {
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
  sheet?: string;
}

export interface CreateTask {
  name: string;
  description: string;
  image: string;
  collaboration_id: number;
  databases: TaskDatabase[];
  organizations: Organization[];
}

export interface KillTask {
  id: number;
}

interface Organization {
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
  organizations: Organization[];
  query?: string;
  sheet_name?: string;
}

// The result of the /column endpoint is either a task or a list of column names
export interface ColumnRetrievalResult extends BaseTask {
  columns?: string[];
}
