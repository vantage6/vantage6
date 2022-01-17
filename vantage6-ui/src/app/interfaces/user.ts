import { Role } from './role';
import { Rule } from './rule';

export interface User {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  organization_id: number;
  roles: Role[];
  rules: Rule[];
  password?: string;
  password_repeated?: string;
  is_being_created?: boolean;
  is_logged_in?: boolean;
}
