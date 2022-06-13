import { deepcopy } from 'src/app/shared/utils';
import { Rule } from 'src/app/interfaces/rule';
import { ResType } from 'src/app/shared/enum';
import { Organization } from './organization';

export interface Role {
  id: number;
  type: string;
  name: string;
  description: string;
  organization_id: number;
  rules: Rule[];
}

export interface RoleWithOrg extends Role {
  organization?: Organization;
}

export const EMPTY_ROLE: Role = {
  id: -1,
  type: ResType.ROLE,
  name: '',
  description: '',
  organization_id: -1,
  rules: [],
};

export function getEmptyRole() {
  return deepcopy(EMPTY_ROLE);
}
