import { deepcopy } from 'src/app/shared/utils';
import { Role } from 'src/app/role/interfaces/role';
import { Rule } from 'src/app/rule/interfaces/rule';
import { ResType } from 'src/app/shared/enum';

export interface User {
  id: number;
  type: string;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  organization_id: number;
  roles: Role[];
  rules: Rule[];
  password?: string;
  password_repeated?: string;
  is_logged_in?: boolean;
}

export const EMPTY_USER: User = {
  id: -1,
  type: ResType.USER,
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  organization_id: -1,
  roles: [],
  rules: [],
};

export function getEmptyUser(): User {
  return deepcopy(EMPTY_USER);
}
