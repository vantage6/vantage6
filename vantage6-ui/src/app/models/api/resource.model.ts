import { AlgorithmStore } from './algorithmStore.model';
import { Collaboration } from './collaboration.model';
import { Node } from './node.model';
import { Organization } from './organization.model';
import { Role } from './role.model';
import { StoreRule } from './rule.model';
import { StoreUser } from './store-user.model';
import { Study } from './study.model';
import { Task, TaskResult, TaskRun } from './task.models';
import { User } from './user.model';

export type Resource =
  | User
  | Organization
  | Collaboration
  | Role
  | Node
  | Task
  | TaskRun
  | TaskResult
  | Study
  | Algorithm
  | AlgorithmStore
  | StoreUser
  | StoreRule;
