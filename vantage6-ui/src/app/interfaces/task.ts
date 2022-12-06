import { Result } from 'src/app/interfaces/result';
import { ResType } from '../shared/enum';
import { deepcopy } from '../shared/utils';
import { Collaboration } from './collaboration';
import { Organization } from './organization';
import { User } from './user';

export interface Task {
  id: number;
  type: string;
  name: string;
  description: string;
  image: string;
  collaboration_id: number;
  collaboration?: Collaboration;
  run_id: number;
  parent_id: number | null;
  parent?: Task;
  database: string;
  initiator_id: number;
  init_org?: Organization;
  init_user_id: number;
  init_user?: User;
  children_ids: number[];
  children?: Task[];
  results?: Result[];
  complete: boolean;
  // data_format?: string;
  input?: TaskInput;
  organizations?: Organization[];
}

export interface KeyValuePairs {
  key: string;
  value: string;
}

export interface TaskInput {
  master: boolean;
  method: string;
  args: string[];
  kwargs: KeyValuePairs[];
}

export const EMPTY_TASK: Task = {
  id: -1,
  type: ResType.TASK,
  name: '',
  description: '',
  image: '',
  database: '',
  collaboration_id: -1,
  initiator_id: -1,
  init_user_id: -1,
  run_id: -1,
  parent_id: -1,
  children_ids: [],
  complete: false,
};

export function getEmptyTask(): Task {
  return deepcopy(EMPTY_TASK);
}

export const EMPTY_TASK_INPUT: TaskInput = {
  master: true,
  method: '',
  args: [],
  kwargs: [],
};

export function getEmptyTaskInput(): TaskInput {
  return deepcopy(EMPTY_TASK_INPUT);
}
