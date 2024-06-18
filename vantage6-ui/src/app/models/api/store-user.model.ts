import { StoreRole } from './store-role.model';
import { StoreServerRegistration } from './store-server';

export enum StoreUserLazyProperties {
  Roles = 'roles'
}

export interface getStoreUserParameters {
  username?: string;
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
