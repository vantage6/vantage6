import { NameDescription } from './base.model';
import { StoreUser } from './store-user.model';
import { Visualization, VisualizationForm } from './visualization.model';

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

export enum AlgorithmStatus {
  // note that this is very similar to ReviewStatus but algorithms contain a few extra statuses
  AwaitingReviewerAssignment = 'awaiting reviewer assignment',
  UnderReview = 'under review',
  Approved = 'approved',
  Rejected = 'rejected',
  Replaced = 'replaced',
  Removed = 'removed'
}

export enum ConditionalArgComparatorType {
  Equal = '==',
  NotEqual = '!=',
  GreaterThan = '>',
  GreaterThanOrEqual = '>=',
  LessThan = '<',
  LessThanOrEqual = '<='
}

// TODO this interface must be updated to match the API
export interface Algorithm {
  id: number;
  name: string;
  image: string;
  digest: string | null;
  vantage6_version: string;
  description: string;
  code_url: string;
  documentation_url?: string;
  submitted_at: string;
  approved_at?: string;
  invalidated_at?: string;
  partitioning: PartitioningType;
  functions: AlgorithmFunction[];
  select?: Select[];
  filter?: Filter[];
  algorithm_store_url?: string;
  algorithm_store_id?: number;
  status: AlgorithmStatus;
  developer_id?: number;
  developer?: StoreUser;
  reviewer?: StoreUser;
}

export interface AlgorithmFunction {
  id: number;
  name: string;
  display_name?: string;
  description: string;
  type: FunctionType;
  arguments: Argument[];
  databases: FunctionDatabase[];
  ui_visualizations: Visualization[];
}

export interface AlgorithmFunctionExtended extends AlgorithmFunction {
  algorithm_id?: number;
  algorithm_name?: string;
  algorithm_store_id?: number;
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
  display_name?: string;
  type: ArgumentType;
  description?: string;
  has_default_value: boolean;
  default_value?: string | number | boolean | null;
  conditional_on_id?: number;
  conditional_operator?: string;
  conditional_value?: string | number | boolean;
}

export interface FunctionDatabase {
  id: number;
  name: string;
  description?: string;
}

export interface ArgumentForm extends NameDescription {
  display_name?: string;
  type: string;
  has_default_value: boolean | string;
  is_default_value_null?: boolean | string;
  default_value?: string | number | boolean | null | string[] | number[] | boolean[];
  hasCondition?: boolean | string;
  conditional_on?: string;
  conditional_operator?: string;
  conditional_value?: string | number | boolean;
}
export interface FunctionForm extends NameDescription {
  display_name?: string;
  arguments: ArgumentForm[];
  databases: NameDescription[];
  ui_visualizations: VisualizationForm[];
  type: string;
}

export interface AlgorithmForm {
  name: string;
  description?: string;
  image: string;
  partitioning: string;
  vantage6_version: string;
  code_url: string;
  documentation_url?: string;
  functions: FunctionForm[];
}
