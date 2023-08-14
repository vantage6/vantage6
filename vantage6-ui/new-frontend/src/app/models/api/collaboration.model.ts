import { BaseOrganization } from './organization.model';

export enum CollaborationLazyProperties {
  Organizations = 'organizations'
}

export interface BaseCollaboration {
  id: number;
  name: string;
  organizations: string;
}

export interface Collaboration {
  id: number;
  name: string;
  organizations: BaseOrganization[];
}
