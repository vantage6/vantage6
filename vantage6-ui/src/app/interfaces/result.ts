import { Port } from 'src/app/interfaces/port';

// TODO include result?
export interface Result {
  id: number;
  type: string;
  name: string;
  input: string;
  result: string;
  log: string | null;
  task_id: number; // TODO necessary?
  organization_id: number;
  ports?: Port[];
  port_ids: number[];
  started_at: Date | null;
  assigned_at: Date | null;
  finished_at: Date | null;
}
