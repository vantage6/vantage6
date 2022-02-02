export enum ExitMode {
  CANCEL = 'CANCEL',
  DELETE = 'DELETE',
}

export enum Resource {
  USER = 'user',
  ORGANIZATION = 'organization',
  COLLABORATION = 'collaboration',
  ROLE = 'role',
  NODE = 'node',
  TASK = 'task',
  RESULT = 'result',
  PORT = 'port',
  ANY = '*',
}

export enum Scope {
  OWN = 'own',
  ORGANIZATION = 'organization',
  COLLABORATION = 'collaboration',
  GLOBAL = 'global',
  ANY = '*',
}

export enum Operation {
  VIEW = 'view',
  CREATE = 'create',
  EDIT = 'edit',
  DELETE = 'delete',
  ANY = '*',
}
