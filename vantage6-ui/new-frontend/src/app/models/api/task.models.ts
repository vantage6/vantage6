import { BaseLink } from './base.model';
import { BaseOrganization } from './organization.model';
import { BaseUser } from './user.model';

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

interface TaskRun {
  input: string;
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
