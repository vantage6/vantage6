import { BaseLink } from './base.model';
import { Organization } from './organization.model';
import { Role } from './role.model';
import { Rule } from './rule.model';

export enum UserLazyProperties {
  Organization = 'organization',
  Roles = 'roles',
  Rules = 'rules'
}

export enum UserSortProperties {
  ID = 'id',
  Username = 'username'
}

export interface GetUserParameters {
  username?: string;
  organization_id?: string;
  collaboration_id?: string;
  sort?: UserSortProperties;
}

export interface BaseUser {
  id: number;
  username: string;
  keycloak_id: string;
  organization: BaseLink;
  roles: string;
  permissions?: UserPermissions;
}

export interface User {
  id: number;
  username: string;
  keycloak_id: string;
  email?: string;
  firstname?: string;
  lastname?: string;
  organization?: Organization;
  roles: Role[];
  rules: Rule[];
}

export interface UserForm {
  username: string;
  password?: string;
  passwordRepeat?: string;
  organization_id: number;
  roles?: number[];
  rules?: number[];
  is_service_account?: boolean;
}

export interface UserPermissions {
  orgs_in_collabs: number[];
  roles: number[];
  rules: number[];
}

export type UserCreate = Pick<UserForm, 'username' | 'password' | 'organization_id' | 'roles' | 'is_service_account'>;

export type UserEdit = Pick<UserForm, 'username' | 'roles'>;
