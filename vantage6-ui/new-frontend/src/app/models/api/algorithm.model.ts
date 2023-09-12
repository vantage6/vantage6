export enum ArgumentType {
  String = 'str',
  Integer = 'int',
  Float = 'float'
}

export enum OutputType {
  Int = 'int',
  Dict = 'dict'
}

export enum OutputVisualizeType {
  Table = 'table'
}

export interface Algorithm {
  id: number;
  name: string;
  url: string;
  functions: Function[];
}

export interface Function {
  name: string;
  is_central: boolean;
  arguments: Argument[];
  databases: Database[];
  output: Output;
}

interface Argument {
  name: string;
  type: ArgumentType;
  description?: string;
}

interface Database {
  name: string;
}
export interface Output {
  type: OutputType;
  keys?: string[] | null;
  visualize?: OutputVisualizeType | null;
}
