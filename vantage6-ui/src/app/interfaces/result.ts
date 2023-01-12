import { Port } from 'src/app/interfaces/port';
import { ResType } from '../shared/enum';
import { deepcopy } from '../shared/utils';
import { Organization } from './organization';

export interface Result {
  id: number;
  type: string;
  input: string;
  result: string;
  log: string | null;
  task_id: number;
  status: string;
  organization_id: number;
  organization?: Organization;
  ports?: Port[];
  port_ids: number[];
  started_at: Date | null;
  assigned_at: Date | null;
  finished_at: Date | null;
  decrypted_result?: string;
}

export const EMPTY_RESULT: Result = {
  id: -1,
  type: ResType.RESULT,
  input: '',
  result: '',
  status: '',
  log: null,
  task_id: -1,
  organization_id: -1,
  port_ids: [],
  started_at: null,
  assigned_at: null,
  finished_at: null,
};

export function getEmptyResult(): Result {
  return deepcopy(EMPTY_RESULT);
}
