import { BaseLink } from './base.model';
import { BaseCollaboration } from './collaboration.model';
import { BaseOrganization } from './organization.model';

export enum NodeLazyProperties {
  Organization = 'organization',
  Collaboration = 'collaboration'
}

export enum NodeSortProperties {
  ID = 'id',
  Name = 'name'
}

export enum DatabaseType {
  CSV = 'csv',
  Excel = 'excel',
  Sparql = 'sparql',
  Parquet = 'parquet',
  SQL = 'sql',
  OMOP = 'omop',
  Other = 'other'
}

export enum NodeStatus {
  Online = 'online',
  Offline = 'offline'
}

export interface GetNodeParameters {
  organization_id?: string;
  collaboration_id?: string;
  sort?: NodeSortProperties;
}

export interface BaseNode {
  id: number;
  name: string;
  organization: BaseLink;
  collaboration: BaseLink;
  config: Config[];
  status?: NodeStatus;
  last_seen?: string;
}

interface Config {
  key: string;
  value: string;
}

export interface Database {
  name: string;
  type: DatabaseType;
}

export interface Node {
  id: number;
  name: string;
  organization?: BaseOrganization;
  collaboration?: BaseCollaboration;
  config: Config[];
  status?: string;
  last_seen?: string;
}

export interface NodeCreate {
  name: string;
  organization_id: number;
  collaboration_id: number;
}

export interface NodeEdit {
  name: string;
}
