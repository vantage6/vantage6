import { Resource } from 'src/app/shared/enum';

import { Result } from 'src/app/result/interfaces/result';

export interface Task {
  id: number;
  type: string;
  name: string;
  description: string;
  image: string;
  collaboration_id: number;
  run_id: number;
  parent_id: number;
  database: string;
  initiator_id: number;
  parent: Task | null;
  children: Task[];
  results: Result[];
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
