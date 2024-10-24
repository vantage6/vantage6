import { StoreRole } from './store-role.model';
import { StoreServerRegistration } from './store-server';

export enum StoreUserLazyProperties {
  Roles = 'roles'
}

export interface GetStoreUserParameters {
  username?: string;
  can_review?: boolean;
  reviewers_for_algorithm_id?: number;
}

export enum StoreUserSortProperties {
  ID = 'id',
  Username = 'username'
}

export interface StoreUser {
  id: number;
  username: string;
  server: StoreServerRegistration;
  roles: StoreRole[];
}

export interface StoreUserForm {
  username: string;
  roles: StoreRole[];
}

export interface StoreUserFormSubmit {
  roles: number[];
}

export interface StoreUserCreate extends StoreUserFormSubmit {
  username: string;
}
