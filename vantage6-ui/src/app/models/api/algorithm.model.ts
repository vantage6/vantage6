export enum ArgumentType {
  String = 'string',
  StringList = 'string_list',
  Integer = 'integer',
  IntegerList = 'integer_list',
  Float = 'float',
  FloatList = 'float_list',
  Column = 'column',
  ColumnList = 'column_list',
  Organization = 'organization',
  OrganizationList = 'organization_list',
  Json = 'json',
  Boolean = 'boolean'
}

export enum OutputType {
  Int = 'int',
  Dict = 'dict'
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

export enum PartitioningType {
  Horizontal = 'horizontal',
  Vertical = 'vertical'
}

export enum FunctionType {
  Central = 'central',
  Federated = 'federated'
}

export enum VisualizationType {
  Table = 'table',
  Histogram = 'histogram'
}

interface VisualizationSchemaBase {
  // defines the type of keys and values that these schemas contain
  [key: string]: string[] | undefined;
}

export interface TableVisualizationSchema extends VisualizationSchemaBase {
  location: string[];
  columns: string[];
}

export interface HistogramVisualizationSchema extends VisualizationSchemaBase {
  [key: string]: string[] | undefined;
  location: string[];
}

export type VisualizationSchema = TableVisualizationSchema | HistogramVisualizationSchema;

// TODO this interface must be updated to match the API
export interface Algorithm {
  id: number;
  name: string;
  image: string;
  vantage6_version: string;
  description: string;
  partitioning: PartitioningType;
  functions: AlgorithmFunction[];
  select?: Select[];
  filter?: Filter[];
  algorithm_store_url?: string;
  algorith_store_id?: number;
}

export interface AlgorithmFunction {
  id: number;
  name: string;
  description: string;
  type: FunctionType;
  arguments: Argument[];
  databases: FunctionDatabase[];
  ui_visualizations: Visualization[];
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

export interface Argument {
  id: number;
  name: string;
  type: ArgumentType;
  description?: string;
}

export interface FunctionDatabase {
  id: number;
  name: string;
  description?: string;
}

export interface Visualization {
  id: number;
  name: string;
  description?: string;
  type: VisualizationType;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  schema?: any;
}

interface NameDescriptionForm {
  name: string;
  description?: string;
}

interface ArgumentForm extends NameDescriptionForm {
  type: string;
}

interface VisualizationForm extends NameDescriptionForm {
  type: VisualizationType;
  schema: VisualizationSchema;
}

interface FunctionForm extends NameDescriptionForm {
  arguments: ArgumentForm[];
  databases: NameDescriptionForm[];
  visualizations: VisualizationForm[];
  type: string;
}

export interface AlgorithmForm {
  name: string;
  description?: string;
  image: string;
  partitioning: string;
  vantage6_version: string;
  functions: FunctionForm[];
}
