import { Role } from './role';
import { Rule } from './rule';

export interface User {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  roles: Role[];
  rules: Rule[];
}
