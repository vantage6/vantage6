import { deepcopy } from 'src/app/shared/utils';
import { Rule } from 'src/app/rule/interfaces/rule';
import { Resource } from 'src/app/shared/enum';

export interface Role {
  id: number;
  type: string;
  name: string;
  description: string;
  organization_id: number | null;
  rules: Rule[];
}

export const EMPTY_ROLE: Role = {
  id: -1,
  type: Resource.ROLE,
  name: '',
  description: '',
  organization_id: null,
  rules: [],
};

export function getEmptyRole() {
  return deepcopy(EMPTY_ROLE);
}
