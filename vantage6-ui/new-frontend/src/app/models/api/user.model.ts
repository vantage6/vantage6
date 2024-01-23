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
  firstname?: string;
  lastname?: string;
  email?: string;
  sort?: UserSortProperties;
}

export interface BaseUser {
  id: number;
  username: string;
  email: string;
  firstname: string;
  lastname: string;
  organization: BaseLink;
  roles: string;
  permissions?: UserPermissions;
}

export interface User {
  id: number;
  username: string;
  email: string;
  firstname: string;
  lastname: string;
  organization?: Organization;
  roles: Role[];
  rules: Rule[];
}

export interface UserForm {
  username: string;
  email: string;
  password: string;
  passwordRepeat: string;
  firstname: string;
  lastname: string;
  organization_id: number;
  roles: number[];
  rules: number[];
}

export interface UserPermissions {
  orgs_in_collabs: number[];
  roles: number[];
  rules: number[];
}

export type UserCreate = Pick<UserForm, 'username' | 'email' | 'password' | 'firstname' | 'lastname' | 'organization_id' | 'roles'>;

export type UserEdit = Pick<UserForm, 'username' | 'email' | 'firstname' | 'lastname' | 'roles'>;
