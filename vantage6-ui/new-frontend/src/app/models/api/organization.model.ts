export enum OrganizationLazyProperties {
  Nodes = 'nodes'
}

export interface BaseOrganization {
  id: number;
  name: string;
  nodes: string;
}

export interface Organization {
  id: number;
  name: string;
  nodes: any[];
}
