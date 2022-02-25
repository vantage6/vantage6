import { Resource } from 'src/app/shared/enum';
import { Port } from 'src/app/port/interfaces/port';

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
  ports: Port[];
  started_at: Date | null;
  assigned_at: Date | null;
  finished_at: Date | null;
}
