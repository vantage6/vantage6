import { deepcopy } from 'src/app/shared/utils';
import { Rule } from 'src/app/rule/interfaces/rule';

export interface Role {
  id: number;
  name: string;
  description: string;
  organization_id: number | null;
  rules: Rule[];
}

export const EMPTY_ROLE: Role = {
  id: -1,
  name: '',
  description: '',
  organization_id: null,
  rules: [],
};

export function getEmptyRole() {
  return deepcopy(EMPTY_ROLE);
}
