import { BaseLink } from './base.model';
import { BaseOrganization } from './organization.model';
import { BaseUser } from './user.model';

export enum SessionLazyProperties {
  InitOrg = 'init_org',
  InitUser = 'init_user'
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

export interface GetSessionParameters {
  collaboration_id?: string;
  name?: string;
  init_user_id?: string;
  sort?: SessionSortProperties;
  parent_id?: number;
  include?: string;
  is_user_created?: number;
}

export interface BaseSession {
  id: number;
  name: string;
  description: string;
  scope: SessionScope;
  image: string;
  init_org: BaseLink;
  init_user: BaseLink;
  algorithm_store?: BaseLink;
  created_at: string;
  parent?: BaseLink;
  study?: BaseLink;
  collaboration?: BaseLink;
}

export interface Session {
  id: number;
  name: string;
  description: string;
  scope: SessionScope;
  image: string;
  init_org?: BaseOrganization;
  init_user?: BaseUser;
  created_at: string;
  parent?: BaseLink;
  study?: BaseLink;
  collaboration?: BaseLink;
  algorithm_store?: BaseLink;
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
