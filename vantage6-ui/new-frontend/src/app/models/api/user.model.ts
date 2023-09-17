import { BaseLink } from './base.model';

export interface BaseUser {
  id: number;
  username: string;
  organization: BaseLink;
}
