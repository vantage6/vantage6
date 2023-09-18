import { BaseLink } from './base.model';
import { BaseOrganization } from './organization.model';
import { BaseUser } from './user.model';
import { NodeStatus } from './node.model';

export enum TaskListParameters {
  collaboration = 'collaboration_id',
  user = 'init_user_id'
}

export enum TaskLazyProperties {
  InitOrg = 'init_org',
  InitUser = 'init_user'
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

export interface BaseTask {
  id: number;
  name: string;
  description: string;
  status: TaskStatus;
  image: string;
  init_org: BaseLink;
  init_user: BaseLink;
  runs: TaskRun[];
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
  result?: string;
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

export interface CreateTask {
  name: string;
  description: string;
  image: string;
  collaboration_id: number;
  databases: string[];
  organizations: Organization[];
}

interface Organization {
  id: number;
  input: string;
}

export interface CreateTaskInput {
  method: string;
  kwargs: Object;
}
