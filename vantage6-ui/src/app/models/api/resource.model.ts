import { AlgorithmForm } from './algorithm.model';
import { AlgorithmStore, AlgorithmStoreForm } from './algorithmStore.model';
import { Collaboration, CollaborationForm } from './collaboration.model';
import { Node } from './node.model';
import { Organization } from './organization.model';
import { ReviewForm } from './review.model';
import { GetRoleParameters, Role, RoleForm } from './role.model';
import { StoreRule } from './rule.model';
import { GetStoreRoleParameters } from './store-role.model';
import { StoreUser, StoreUserForm, GetStoreUserParameters } from './store-user.model';
import { Study } from './study.model';
import { Task, TaskResult, TaskRun } from './task.models';
import { GetUserParameters, User, UserForm } from './user.model';

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

export type ResourceForm = UserForm | CollaborationForm | RoleForm | AlgorithmForm | AlgorithmStoreForm | StoreUserForm | ReviewForm;

export type ResourceGetParameters = GetRoleParameters | GetUserParameters | GetStoreUserParameters | GetStoreRoleParameters;
