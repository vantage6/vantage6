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
  Table = 'table',
  TableGrouped = 'table_grouped',
  Histogram = 'histogram'
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
  output: Output[];
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
  visualize?: OutputVisualizeType | null;
  title?: string;
  type: OutputType;
  keys?: string[] | null;
  filter_property?: string;
  filter_value?: string;
}
