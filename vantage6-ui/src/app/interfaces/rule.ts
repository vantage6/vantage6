export enum Resource {
  USER = 'user',
  ORGANIZATION = 'organization',
  COLLABORATION = 'collaboration',
  ROLE = 'role',
  NODE = 'node',
  TASK = 'task',
  RESULT = 'result',
  PORT = 'port',
}
export enum Scope {
  OWN = 'own',
  ORGANIZATION = 'organization',
  COLLABORATION = 'collaboration',
  GLOBAL = 'global',
}
export enum Operation {
  VIEW = 'view',
  CREATE = 'create',
  EDIT = 'edit',
  DELETE = 'delete',
}

export interface Rule {
  id: number;
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
