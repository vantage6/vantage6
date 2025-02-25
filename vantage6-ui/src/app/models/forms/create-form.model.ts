import { CreateTaskOrganization } from '../api/task.models';

export interface FormCreateOutput {
  name: string;
  description?: string;
  image?: string;
  session_id?: number;
  collaboration_id?: number;
  study_id?: number;
  store_id?: number;
  server_url?: string;
  database?: string;
  dataframes?: any[];
  organizations?: CreateTaskOrganization[];
}

export interface AvailableSteps {
  session: boolean;
  study: boolean;
  function: boolean;
  database: boolean;
  dataframe: boolean;
  preprocessing: boolean;
  filter: boolean;
  parameter: boolean;
}
