export interface Rule {
  id: number;
  type: string;
  resource: string;
  scope: string;
  is_part_role?: boolean;
}

export interface RuleGroup {
  resource: string;
  scope: string;
  rules: Rule[];
}
