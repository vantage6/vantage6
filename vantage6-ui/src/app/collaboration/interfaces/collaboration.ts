import { OrganizationInCollaboration } from 'src/app/organization/interfaces/organization';

export interface Collaboration {
  id: number;
  name: string;
  encrypted: boolean;
  organizations: OrganizationInCollaboration[];
}

export const EMPTY_COLLABORATION = {
  id: -1,
  name: '',
  encrypted: true,
  organizations: [],
};
