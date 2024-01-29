import { ResourceType, ScopeType } from '../api/rule.model';

export interface NavigationLink {
  route: string;
  label: string;
  icon: string;
  resource?: ResourceType;
  scope?: ScopeType[];
  shouldBeExact?: boolean;
}
