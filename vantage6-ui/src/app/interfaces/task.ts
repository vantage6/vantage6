import { Result } from 'src/app/interfaces/result';
import { Collaboration } from './collaboration';
import { Organization } from './organization';

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
  initiator?: Organization;
  children_ids: number[];
  children?: Task[];
  results?: Result[];
  complete: boolean;
}

// export const EMPTY_USER: User = {
//   id: -1,
//   type: Resource.USER,
//   username: '',
//   email: '',
//   first_name: '',
//   last_name: '',
//   organization_id: -1,
//   roles: [],
//   rules: [],
// };

// export function getEmptyUser(): User {
//   return deepcopy(EMPTY_USER);
// }
