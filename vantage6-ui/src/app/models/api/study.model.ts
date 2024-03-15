import { BaseCollaboration } from './collaboration.model';
import { BaseOrganization } from './organization.model';

export interface BaseStudy {
  id: number;
  name: string;
}

export interface Study {
  id: number;
  name: string;
  organizations: BaseOrganization[];
  collaboration?: BaseCollaboration;
}

export interface GetStudyParameters {
  name?: string;
  organization_id?: number;
}

export enum StudyLazyProperties {
  Organizations = 'organizations',
  Collaboration = 'collaboration'
}

export interface StudyForm {
  name: string;
  organizations: BaseOrganization[];
}

export type StudyEdit = {
  name: string;
  organization_ids: number[];
};
export type StudyCreate = StudyEdit & { collaboration_id: number };

export enum StudyOrCollab {
  Study = 'study',
  Collaboration = 'collaboration'
}
