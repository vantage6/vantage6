import { ResourceType, ScopeType } from 'src/app/models/api/rule.model';

export enum NavigationLinkType {
  Home = 'home',
  Analyze = 'analyze',
  Admin = 'admin',
  Store = 'store',
  Other = 'other'
}

export interface NavigationLink {
  route: string;
  label: string;
  icon: string;
  linkType: NavigationLinkType;
  resource?: ResourceType;
  scope?: ScopeType[];
  shouldBeExact?: boolean;
  submenus?: NavigationLink[];
  expanded?: boolean;
}
