export enum ExitMode {
  CANCEL = 'CANCEL',
  DELETE = 'DELETE',
  EDIT = 'EDIT',
}

export enum ResType {
  USER = 'user',
  ORGANIZATION = 'organization',
  COLLABORATION = 'collaboration',
  ROLE = 'role',
  NODE = 'node',
  TASK = 'task',
  RESULT = 'result',
  EVENT = 'event',
  PORT = 'port',
  RULE = 'rule',
  ANY = '*',
}

export enum ScopeType {
  OWN = 'own',
  ORGANIZATION = 'organization',
  COLLABORATION = 'collaboration',
  GLOBAL = 'global',
  ANY = '*',
}

export enum OpsType {
  VIEW = 'view',
  CREATE = 'create',
  EDIT = 'edit',
  DELETE = 'delete',
  SEND = 'send',
  ANY = '*',
}
