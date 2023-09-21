import { Collaboration } from 'src/app/interfaces/collaboration';
import { User } from 'src/app/interfaces/user';
import { Role, RoleWithOrg } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { Node, NodeWithOrg } from 'src/app/interfaces/node';
import { Organization } from 'src/app/interfaces/organization';
import { Task } from 'src/app/interfaces/task';
import { Run } from '../interfaces/run';

export type Resource =
  | User
  | Role
  | Rule
  | Organization
  | Collaboration
  | Node
  | Task
  | Run;

export type ResourceWithOrg = RoleWithOrg | User | NodeWithOrg;

export type ResourceInOrg = User | Role | Node;

export type ResourceInCollab = Node;
