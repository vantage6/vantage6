import { Collaboration } from 'src/app/interfaces/collaboration';
import { User, UserWithOrg } from 'src/app/interfaces/user';
import { Role, RoleWithOrg } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { Node, NodeWithOrg } from 'src/app/interfaces/node';
import { Organization } from 'src/app/interfaces/organization';

export type Resource = User | Role | Rule | Organization | Collaboration | Node;

export type ResourceWithOrg = RoleWithOrg | UserWithOrg | NodeWithOrg;

export type ResourceInOrg = User | Role | Node;
