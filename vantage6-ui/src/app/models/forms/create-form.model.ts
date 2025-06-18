import { CreateTaskOrganization } from '../api/task.models';

export interface FormCreateOutput {
  name: string;
  description?: string;
  image: string;
  method: string;
  session_id: number;
  organizations: CreateTaskOrganization[];
  store_id: number;
  collaboration_id?: number;
  study_id?: number;
  database?: string;
  dataframes?: any[];
}

export interface AvailableSteps {
  session: boolean;
  study: boolean;
  function: boolean;
  database: boolean;
  dataframe: boolean;
  parameter: boolean;
}

export enum AvailableStepsEnum {
  Session = 'session',
  Study = 'study',
  Function = 'function',
  Database = 'database',
  Dataframe = 'dataframe',
  Parameter = 'parameter'
}
