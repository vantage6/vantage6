import { BaseLink } from './base.model';
import { Organization } from './organization.model';
import { Role } from './role.model';

export enum UserLazyProperties {
  Organization = 'organization',
  Roles = 'roles'
}

export interface BaseUser {
  id: number;
  username: string;
  email: string;
  firstname: string;
  lastname: string;
  organization: BaseLink;
  roles: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  firstname: string;
  lastname: string;
  organization?: Organization;
  roles: Role[];
}
