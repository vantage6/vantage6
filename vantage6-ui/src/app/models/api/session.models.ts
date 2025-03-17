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
  Global = 'global',
  Collaboration = 'collaboration',
  Organization = 'organization',
  Own = 'own'
}


export enum TaskDatabaseType {
  Dataframe = 'dataframe',
  Source = 'source'
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
}
// TODO(BART/RIAN) RIAN: Only the user who initiated the session will be displayed. Consider including more information and looking at the scope of
// what should be displayed. For example: scope = organization, then show the initiating organization.

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

export interface Dataframe {
  // Frank: Dataframe => source database inituser status description algorithm function parameters runs => looks like taks
  // Actual response:
  // columns: []
  // name: "TestDFnogeens"
  // id: 2
  // last_session_task: {image: 'harbor2.vantage6.ai/demo/average@sha256:ce3ebaacac…de7c552ebc86f9bf2252f18fee0b67965ed94d0bd78e5174c', id: 3, depends_on: Array(0), study: {…}, children: '/api/task?parent_id=3', …}
  // ready: true
  // session: {id: 2, link: '/api/session/2', methods: Array(3)}
  // tasks: "/api/task?dataframe_id=2"
  //
  // TODO(BART/RIAN) RIAN: Customize the request and response of dataframes in the backend and process this information in the UI.
  name: string;
  db_label: string;
  id: number;
  tasks: string;
  last_session_task: BaseTask;
}

export interface CreateDataframe {
  name: string;
  label: string;
  task: CreateDataframeTask;
}

interface CreateDataframeTask {
  image: string;
  organizations: CreateTaskOrganization[];
  store_id?: number;
}
