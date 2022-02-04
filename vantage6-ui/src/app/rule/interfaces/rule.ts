import { Operation, Resource, Scope } from 'src/app/shared/enum';

export interface Rule {
  id: number;
  type: string;
  operation: Operation;
  resource: Resource;
  scope: Scope;
  is_part_role?: boolean;
  is_assigned_to_user?: boolean;
  is_assigned_to_loggedin?: boolean;
}

export interface RuleGroup {
  resource: string;
  scope: string;
  rules: Rule[];
}
