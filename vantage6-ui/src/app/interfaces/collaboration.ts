import { OrganizationInCollaboration } from 'src/app/interfaces/organization';
import { ResType } from 'src/app/shared/enum';

export interface Collaboration {
  id: number;
  type: ResType;
  name: string;
  encrypted: boolean;
  organizations: OrganizationInCollaboration[];
}

export const EMPTY_COLLABORATION = {
  id: -1,
  name: '',
  type: ResType.COLLABORATION,
  encrypted: true,
  organizations: [],
};
