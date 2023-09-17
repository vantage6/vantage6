import { BaseCollaboration } from './Collaboration.model';
import { BaseNode } from './node.model';

export enum OrganizationLazyProperties {
  Nodes = 'nodes',
  Collaborations = 'collaborations'
}

export interface BaseOrganization {
  id: number;
  name: string;
  address1: string;
  address2: string;
  country: string;
  domain: string;
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
  nodes: BaseNode[];
  collaborations: BaseCollaboration[];
}
