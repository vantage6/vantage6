import { BaseNode } from './node.model';
import { BaseOrganization } from './organization.model';
import { BaseTask } from './task.models';

export enum CollaborationLazyProperties {
  Organizations = 'organizations',
  Nodes = 'nodes',
  Tasks = 'tasks'
}

export interface BaseCollaboration {
  id: number;
  name: string;
  encrypted: boolean;
  organizations: string;
  nodes: string;
  tasks: string;
}

export interface Collaboration {
  id: number;
  name: string;
  encrypted: boolean;
  organizations: BaseOrganization[];
  nodes: BaseNode[];
  tasks: BaseTask[];
}

export interface CollaborationCreate {
  name: string;
  encrypted: boolean;
  organization_ids: number[];
}
