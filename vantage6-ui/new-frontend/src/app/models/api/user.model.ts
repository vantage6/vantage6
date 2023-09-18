import { BaseLink } from './base.model';

export interface BaseUser {
  id: number;
  username: string;
  email: string;
  firstname: string;
  lastname: string;
  organization: BaseLink;
}
