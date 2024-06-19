import { RoleSortProperties } from './role.model';

export interface StoreRole {
  id: number;
  description: string;
  name: string;
}

export interface GetStoreRoleParameters {
  name?: string;
  sort?: RoleSortProperties;
  user_id?: number;
}
