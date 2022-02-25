import { OpsType, ResType, ScopeType } from 'src/app/shared/enum';

export interface Rule {
  id: number;
  type: string;
  operation: OpsType;
  resource: ResType;
  scope: ScopeType;
  is_part_role?: boolean;
  is_assigned_to_user?: boolean;
  is_assigned_to_loggedin?: boolean;
}

export interface RuleGroup {
  resource: string;
  scope: string;
  rules: Rule[];
}
