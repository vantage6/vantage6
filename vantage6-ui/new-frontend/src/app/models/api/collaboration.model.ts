import { BaseNode } from './node.model';
import { BaseOrganization } from './organization.model';
import { BaseTask } from './task.models';

export enum CollaborationLazyProperties {
  Organizations = 'organizations',
  Nodes = 'nodes',
  Tasks = 'tasks'
}

export enum CollaborationSortProperties {
  ID = 'id',
  Name = 'name'
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

export interface CollaborationForm {
  name: string;
  encrypted: boolean;
  organization_ids: number[];
  registerNodes: boolean;
}

export type CollaborationCreate = Pick<CollaborationForm, 'name' | 'encrypted' | 'organization_ids'>;
