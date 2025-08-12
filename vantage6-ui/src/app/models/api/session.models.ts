import { BaseLink } from './base.model';
import { BaseTask, CreateTaskOrganization } from './task.models';
import { BaseUser } from './user.model';

export enum SessionLazyProperties {
  Owner = 'owner'
}

export enum SessionSortProperties {
  ID = 'id',
  Name = 'name'
}

export enum SessionScope {
  Collaboration = 'collaboration',
  Organization = 'organization',
  Own = 'own'
}

export enum TaskDatabaseType {
  Dataframe = 'dataframe',
  Source = 'source'
}

export enum AlgorithmStepType {
  Preprocessing = 'preprocessing',
  DataExtraction = 'data_extraction',
  FederatedCompute = 'federated_compute',
  CentralCompute = 'central_compute',
  Postprocessing = 'postprocessing'
}

export interface GetSessionParameters {
  collaboration_id?: string;
  name?: string;
  init_user_id?: string;
  sort?: SessionSortProperties;
  include?: string;
}

export interface BaseSession {
  id: number;
  name: string;
  scope: SessionScope;
  ready: boolean;
  created_at: string;
  last_used_at: string;
  owner: BaseLink;
  study?: BaseLink;
  collaboration?: BaseLink;
  dataframes: string[];
  tasks: string[];
}

export interface Session {
  id: number;
  name: string;
  scope: SessionScope;
  ready: boolean;
  created_at: string;
  last_used_at: string;
  owner?: BaseUser;
  study?: BaseLink;
  collaboration?: BaseLink;
  dataframes: string[];
  tasks: string[];
  image?: string;
}

export interface CreateSession {
  name: string;
  scope: SessionScope;
  collaboration_id: number;
  study_id?: number;
}

export interface ColumnRetrievalInput {
  collaboration_id: number;
  db_label: string;
  query?: string;
  sheet_name?: string;
}

export interface ColumnRetrievalResult extends BaseSession {
  columns?: string[];
}

interface DataframeColumn {
  name: string;
  dtype: string;
  node_id: number;
}

export interface DataframeColumnTableDisplay {
  name: string;
  type: string;
  node_names: string[];
}

export interface Dataframe {
  name: string;
  db_label: string;
  id: number;
  tasks: string;
  last_session_task: BaseTask;
  columns: DataframeColumn[];
  ready: boolean;
  organizations_ready: number[];
  session: BaseLink;
}

export interface CreateDataframe {
  name: string;
  label: string;
  task: DataframeTask;
}

export interface DataframePreprocess {
  dataframe_id: number;
  task: DataframeTask;
}

interface DataframeTask {
  image: string;
  method: string;
  organizations: CreateTaskOrganization[];
  store_id?: number;
}

export interface GetDataframeParameters {
  name?: string;
}
