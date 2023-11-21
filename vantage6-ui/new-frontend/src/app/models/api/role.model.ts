import { Rule } from './rule.model';
import { BaseUser } from './user.model';

export interface BaseRole {
  id: number;
  description: string;
  name: string;
  rules: string;
  users: string;
}

export interface Role {
  id: number;
  description: string;
  name: string;
  rules: Rule[];
  users: BaseUser[];
}

export enum RoleLazyProperties {
  Rules = 'rules',
  Users = 'users'
}

export enum RoleSortProperties {
  ID = 'id',
  Name = 'name'
}

export interface GetRoleParameters {
  organization_id?: string;
  sort?: RoleSortProperties;
}

export interface RolePatch {
  description: string;
  name: string;
  rules: number[];
}
