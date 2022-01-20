import { Rule } from './rule';

export interface Role {
  id: number;
  name: string;
  description: string;
  organization_id: number | null;
  rules: Rule[];
  is_being_edited?: boolean;
}

export const EMPTY_ROLE: Role = {
  id: -1,
  name: '',
  description: '',
  organization_id: null,
  rules: [],
};
