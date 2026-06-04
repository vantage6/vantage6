import { AlgorithmStore } from './algorithmStore.model';
import { BaseNode } from './node.model';
import { BaseOrganization } from './organization.model';
import { BaseStudy } from './study.model';
import { BaseTask } from './task.models';

export enum CollaborationLazyProperties {
  Organizations = 'organizations',
  Nodes = 'nodes',
  Tasks = 'tasks',
  AlgorithmStores = 'algorithm_stores',
  Studies = 'studies'
}

export enum CollaborationSortProperties {
  ID = 'id',
  Name = 'name'
}

export interface GetCollaborationParameters {
  name?: string;
  organization_id?: string;
  sort?: CollaborationSortProperties;
}

export interface BaseCollaboration {
  id: number;
  name: string;
  encrypted: boolean;
  session_restrict_to_same_image: boolean;
  organizations: string;
  nodes: string;
  tasks: string;
  algorithm_stores: string;
}

export interface Collaboration {
  id: number;
  name: string;
  encrypted: boolean;
  session_restrict_to_same_image: boolean;
  organizations: BaseOrganization[];
  nodes: BaseNode[];
  tasks: BaseTask[];
  algorithm_stores: AlgorithmStore[];
  studies: BaseStudy[];
}

export interface CollaborationForm {
  name: string;
  encrypted: boolean;
  session_restrict_to_same_image: boolean;
  organizations: BaseOrganization[];
  registerNodes: boolean;
}

export type CollaborationCreate = {
  name: string;
  encrypted: boolean;
  session_restrict_to_same_image?: boolean;
  organization_ids: number[];
};
