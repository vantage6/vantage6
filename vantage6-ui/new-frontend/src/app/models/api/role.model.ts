export interface Role {
  id: number;
  name: string;
}

export enum RoleSortProperties {
  ID = 'id',
  Name = 'name'
}

export interface GetRoleParameters {
  organization_id?: string;
  sort?: RoleSortProperties;
}
