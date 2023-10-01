import { BaseLink } from './base.model';
import { BaseCollaboration, Collaboration } from './collaboration.model';
import { BaseOrganization, Organization } from './organization.model';

export enum NodeLazyProperties {
  Organization = 'organization',
  Collaboration = 'collaboration'
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

export interface BaseNode {
  id: number;
  name: string;
  organization: BaseLink;
  collaboration: BaseLink;
  config: Config[];
  status?: string;
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
