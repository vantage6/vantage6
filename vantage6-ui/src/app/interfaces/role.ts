import { Rule } from './rule';

export interface Role {
  id: number;
  name: string;
  description: string;
  organization_id: number | null;
  rules: Rule[];
  // permissions: Permission;
}
