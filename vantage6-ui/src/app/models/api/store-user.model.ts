import { StoreServerRegistration } from './store-server';

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
}
