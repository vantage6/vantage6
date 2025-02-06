export enum ResourceType {
  USER = 'user',
  ORGANIZATION = 'organization',
  COLLABORATION = 'collaboration',
  ROLE = 'role',
  NODE = 'node',
  SESSION = 'session',
  TASK = 'task',
  RUN = 'run',
  RESULT = 'result',
  EVENT = 'event',
  PORT = 'port',
  RULE = 'rule',
  STUDY = 'study',
  ANY = '*'
}

export enum StoreResourceType {
  ALGORITHM = 'algorithm',
  USER = 'user',
  ROLE = 'role',
  VANTAGE6_SERVER = 'vantage6_server',
  REVIEW = 'review',
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

interface BaseRule {
  id: number;
  type: string;
  operation: OperationType;
}

export interface Rule extends BaseRule {
  scope: ScopeType;
  name: ResourceType;
}

export interface StoreRule extends BaseRule {
  name: StoreResourceType;
}

export type Rule_ = Rule | StoreRule;

interface BaseGetRuleParameters {
  no_pagination?: 0 | 1;
  role_id?: string;
}

export interface GetRuleParameters extends BaseGetRuleParameters {
  user_id?: number;
}

export interface GetStoreRuleParameters extends BaseGetRuleParameters {
  username?: string;
  server_url?: string;
}
