import { RoleSortProperties } from './role.model';
import { StoreRule } from './rule.model';
import { StoreUser } from './store-user.model';

export enum StoreRoleLazyProperties {
  Users = 'users',
  Rules = 'rules'
}

export interface StoreRole {
  id: number;
  description: string;
  name: string;
  rules: StoreRule[];
  users?: StoreUser[];
}

export interface GetStoreRoleParameters {
  name?: string;
  sort?: RoleSortProperties;
  user_id?: number;
}

export interface StoreRoleForm {
  name: string;
  description: string;
  rules: number[];
}

export interface StoreRoleCreate {
  name: string;
  description: string;
  rules: number[];
}
