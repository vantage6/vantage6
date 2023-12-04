export enum ArgumentType {
  String = 'str',
  Integer = 'int',
  Float = 'float',
  Json = 'json'
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

export enum SelectParameterType {
  Column = 'column',
  String = 'string',
  Integer = 'integer',
  Float = 'float',
  Boolean = 'bool',
  Date = 'date'
}

export enum FilterParameterType {
  Column = 'column',
  String = 'string',
  Integer = 'integer',
  Float = 'float',
  Boolean = 'bool',
  Date = 'date'
}

export interface BaseAlgorithm {
  id: number;
  name: string;
  url: string;
}

export interface Algorithm {
  id: number;
  name: string;
  url: string;
  functions: AlgorithmFunction[];
  select: Select[];
  filter: Filter[];
}

export interface AlgorithmFunction {
  name: string;
  is_central: boolean;
  arguments: Argument[];
  databases: FunctionDatabase[];
  output: Output[];
}

export interface Select {
  function: string;
  description?: string;
  parameters: SelectParameter[];
}

export interface Filter {
  function: string;
  description?: string;
  parameters: FilterParameter[];
}

export interface SelectParameter {
  name: string;
  type: SelectParameterType;
  description: string;
  required: boolean;
  default?: string | boolean;
}

export interface FilterParameter {
  name: string;
  type: FilterParameterType;
  description: string;
  required: boolean;
  default?: string | boolean;
}

interface Argument {
  name: string;
  type: ArgumentType;
  description?: string;
}

export interface FunctionDatabase {
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
