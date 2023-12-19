import { Rule } from './rule.model';
import { BaseUser } from './user.model';

export interface BaseRole {
  id: number;
  description: string;
  name: string;
  rules: string;
  users: string;
}

export interface RoleOrganization {
  id: number;
  link: string;
}

export interface Role {
  id: number;
  description: string;
  name: string;
  rules: Rule[];
  users: BaseUser[];
  organization?: RoleOrganization;
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
  user_id?: number;
  per_page?: number;
}

export interface RolePatch {
  name: string;
  description: string;
  rules: number[];
}

export interface RoleForm {
  name: string;
  description: string;
  organization_id: number;
  rules: number[];
}

export interface RoleCreate {
  name: string;
  description: string;
  organization_id: number;
  rules: number[];
}
