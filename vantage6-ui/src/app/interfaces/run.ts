import { Port } from 'src/app/interfaces/port';
import { ResType } from '../shared/enum';
import { deepcopy } from '../shared/utils';
import { Organization } from './organization';

export interface Run {
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

export const EMPTY_RUN: Run = {
  id: -1,
  type: ResType.RUN,
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

export function getEmptyRun(): Run {
  return deepcopy(EMPTY_RUN);
}
