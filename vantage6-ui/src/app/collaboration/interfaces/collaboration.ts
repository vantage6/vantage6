import { OrganizationInCollaboration } from 'src/app/organization/interfaces/organization';
import { Resource } from 'src/app/shared/enum';

export interface Collaboration {
  id: number;
  type: Resource;
  name: string;
  encrypted: boolean;
  organizations: OrganizationInCollaboration[];
}

export const EMPTY_COLLABORATION = {
  id: -1,
  name: '',
  type: Resource.COLLABORATION,
  encrypted: true,
  organizations: [],
};
