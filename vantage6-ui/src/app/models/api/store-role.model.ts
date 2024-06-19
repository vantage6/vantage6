import { RoleSortProperties } from './role.model';
import { StoreUser } from './store-user.model';

export enum StoreRoleLazyProperties {
  Users = 'users'
}

export interface StoreRole {
  id: number;
  description: string;
  name: string;
  users?: StoreUser[];
}

export interface GetStoreRoleParameters {
  name?: string;
  sort?: RoleSortProperties;
  user_id?: number;
}
