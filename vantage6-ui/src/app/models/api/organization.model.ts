import { BaseCollaboration } from './collaboration.model';
import { BaseNode } from './node.model';

export enum OrganizationLazyProperties {
  Nodes = 'nodes',
  Collaborations = 'collaborations'
}

export enum OrganizationSortProperties {
  ID = 'id',
  Name = 'name'
}

export interface GetOrganizationParameters {
  name?: string;
  collaboration_id?: string;
  study_id?: number;
  sort?: OrganizationSortProperties;
}

export interface BaseOrganization {
  id: number;
  name: string;
  address1: string;
  address2: string;
  country: string;
  domain: string;
  public_key: string;
  nodes: string;
  collaborations: string;
}

export interface Organization {
  id: number;
  name: string;
  address1: string;
  address2: string;
  country: string;
  domain: string;
  public_key: string;
  nodes: BaseNode[];
  collaborations: BaseCollaboration[];
}

export interface OrganizationCreate {
  name: string;
  address1?: string | null;
  address2?: string | null;
  country?: string | null;
  domain?: string | null;
  public_key?: string | null;
}
