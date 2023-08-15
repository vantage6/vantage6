export enum ArgumentType {
  String = 'str',
  Integer = 'int',
  Float = 'float'
}

export interface Algorithm {
  id: number;
  name: string;
  functions: Function[];
}

export interface Function {
  name: string;
  is_central: boolean;
  arguments: Argument[];
  databases: Database[];
}

interface Argument {
  name: string;
  type: ArgumentType;
  description?: string;
}

interface Database {
  name: string;
}
