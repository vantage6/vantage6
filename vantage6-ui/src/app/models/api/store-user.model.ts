import { BaseStoreRole } from './store-role.model';
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
  roles: BaseStoreRole[];
}
