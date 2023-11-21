export enum ResourceType {
  USER = 'user',
  ORGANIZATION = 'organization',
  COLLABORATION = 'collaboration',
  ROLE = 'role',
  NODE = 'node',
  TASK = 'task',
  RUN = 'run',
  RESULT = 'result',
  EVENT = 'event',
  PORT = 'port',
  RULE = 'rule',
  ANY = '*'
}

export enum ScopeType {
  OWN = 'own',
  ORGANIZATION = 'organization',
  COLLABORATION = 'collaboration',
  GLOBAL = 'global',
  ANY = '*'
}

export enum OperationType {
  VIEW = 'view',
  CREATE = 'create',
  EDIT = 'edit',
  DELETE = 'delete',
  SEND = 'send',
  RECEIVE = 'receive',
  ANY = '*'
}

export interface Rule {
  id: number;
  type: string;
  operation: OperationType;
  name: ResourceType; //TODO: should be named resource in backend
  scope: ScopeType;
}

export interface GetRuleParameters {
  no_pagination?: 0 | 1;
  role_id?: string;
}
