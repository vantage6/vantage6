import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { OpsType, ResType, ScopeType } from './shared/enum';
import {
  AccessGuard,
  AccessGuardByOrgId,
  OrgAccessGuard,
} from 'src/app/auth/access-guard.guard';

import { HomeComponent } from './components/home/home.component';
import { OrganizationComponent } from './components/organization/organization.component';
import { UserEditComponent } from './components/edit/user-edit/user-edit.component';
import { RoleEditComponent } from './components/edit/role-edit/role-edit.component';
import { OrganizationEditComponent } from './components/edit/organization-edit/organization-edit.component';
import { CollaborationEditComponent } from './components/edit/collaboration-edit/collaboration-edit.component';
import { RoleTableComponent } from './components/table/role-table/role-table.component';
import { UserTableComponent } from './components/table/user-table/user-table.component';
import { NodeTableComponent } from './components/table/node-table/node-table.component';
import { CollaborationViewSingleComponent } from './components/view-single/collaboration-view-single/collaboration-view-single.component';
import { TaskTableComponent } from './components/table/task-table/task-table.component';
import { TaskViewSingleComponent } from './components/view-single/task-view-single/task-view-single.component';
import { ProfileComponent } from './components/profile/profile.component';
import { CollaborationTableComponent } from './components/table/collaboration-table/collaboration-table.component';
import { RoleViewSingleComponent } from './components/view-single/role-view-single/role-view-single.component';
import { UserViewSingleComponent } from './components/view-single/user-view-single/user-view-single.component';
import { NodeSingleViewComponent } from './components/view-single/node-single-view/node-single-view.component';
import { LoginPageComponent } from './components/login/login-page/login-page.component';
import { SocketMessagesComponent } from './components/table/socket-messages/socket-messages.component';

const routes: Routes = [
  {
    path: 'login',
    component: LoginPageComponent,
  },
  {
    path: 'password_lost',
    component: LoginPageComponent,
  },
  {
    path: 'password_recover',
    component: LoginPageComponent,
  },
  {
    path: 'home',
    component: HomeComponent,
    data: { requiresLogin: true },
    canActivate: [AccessGuard],
  },
  { path: '', redirectTo: '/home', pathMatch: 'full' },
  {
    path: 'profile',
    component: ProfileComponent,
    data: { requiresLogin: true },
    canActivate: [AccessGuard],
  },
  {
    path: 'organization/create',
    component: OrganizationEditComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.CREATE,
      permissionResource: ResType.ORGANIZATION,
      permissionScope: ScopeType.GLOBAL,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'organization/:id',
    component: OrganizationComponent,
    data: {
      permissionType: OpsType.VIEW,
    },
    canActivate: [OrgAccessGuard],
  },
  {
    path: 'organization/:id/edit',
    component: OrganizationEditComponent,
    data: {
      permissionType: OpsType.EDIT,
    },
    canActivate: [OrgAccessGuard],
  },
  {
    path: 'user/create/:org_id',
    component: UserEditComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.CREATE,
      permissionResource: ResType.USER,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'user/create',
    component: UserEditComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.CREATE,
      permissionResource: ResType.USER,
      permissionScope: ScopeType.GLOBAL,
    },
    canActivate: [AccessGuard],
  },
  {
    // TODO think what happens if a user tries to go to edit a user that they're
    // not allowed to edit, by directly going to the path? Does it work? Otherwise,
    // change the accessguard
    path: 'user/:id/edit',
    component: UserEditComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.EDIT,
      permissionResource: ResType.USER,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'role/create/:org_id',
    component: RoleEditComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.CREATE,
      permissionResource: ResType.ROLE,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'role/create',
    component: RoleEditComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.CREATE,
      permissionResource: ResType.ROLE,
      permissionScope: ScopeType.GLOBAL,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'role/:id/edit',
    component: RoleEditComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.EDIT,
      permissionResource: ResType.ROLE,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'node/:id/view/:org_id',
    component: NodeSingleViewComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.VIEW,
      permissionResource: ResType.NODE,
    },
    canActivate: [AccessGuardByOrgId],
  },
  {
    path: 'collaboration/create',
    component: CollaborationEditComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.CREATE,
      permissionResource: ResType.COLLABORATION,
      permissionScope: ScopeType.GLOBAL,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'collaboration/:id/edit',
    component: CollaborationEditComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.EDIT,
      permissionResource: ResType.COLLABORATION,
      permissionScope: ScopeType.GLOBAL,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'collaboration/:id/:org_id',
    component: CollaborationViewSingleComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.VIEW,
      permissionResource: ResType.COLLABORATION,
    },
    canActivate: [AccessGuardByOrgId],
  },
  {
    path: 'roles',
    component: RoleTableComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.VIEW,
      permissionResource: ResType.ROLE,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'roles/:org_id',
    component: RoleTableComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.VIEW,
      permissionResource: ResType.ROLE,
    },
    canActivate: [AccessGuardByOrgId],
  },
  {
    path: 'users',
    component: UserTableComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.VIEW,
      permissionResource: ResType.USER,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'users/:org_id',
    component: UserTableComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.VIEW,
      permissionResource: ResType.USER,
    },
    canActivate: [AccessGuardByOrgId],
  },
  {
    path: 'collaborations',
    component: CollaborationTableComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.VIEW,
      permissionResource: ResType.COLLABORATION,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'collaborations/:org_id',
    component: CollaborationTableComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.VIEW,
      permissionResource: ResType.COLLABORATION,
    },
    canActivate: [AccessGuardByOrgId],
  },
  {
    path: 'nodes',
    component: NodeTableComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.VIEW,
      permissionResource: ResType.NODE,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'nodes/org/:org_id',
    component: NodeTableComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.VIEW,
      permissionResource: ResType.NODE,
    },
    canActivate: [AccessGuardByOrgId],
  },
  {
    path: 'nodes/collab/:collab_id',
    component: NodeTableComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.VIEW,
      permissionResource: ResType.NODE,
      permissionScope: ScopeType.GLOBAL,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'tasks',
    component: TaskTableComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.VIEW,
      permissionResource: ResType.TASK,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'tasks/org/:org_id',
    component: TaskTableComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.VIEW,
      permissionResource: ResType.TASK,
    },
    canActivate: [AccessGuardByOrgId],
  },
  {
    path: 'tasks/collab/:collab_id',
    component: TaskTableComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.VIEW,
      permissionResource: ResType.TASK,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'task/view/:id/:org_id',
    component: TaskViewSingleComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.VIEW,
      permissionResource: ResType.TASK,
    },
    canActivate: [AccessGuardByOrgId],
  },
  {
    path: 'role/view/:id/:org_id',
    component: RoleViewSingleComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.VIEW,
      permissionResource: ResType.ROLE,
    },
    canActivate: [AccessGuardByOrgId],
  },
  {
    path: 'user/view/:id/:org_id',
    component: UserViewSingleComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.VIEW,
      permissionResource: ResType.USER,
    },
    canActivate: [AccessGuardByOrgId],
  },
  {
    path: 'status-messages',
    component: SocketMessagesComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.VIEW,
      permissionResource: ResType.EVENT,
    },
  },
];
//TODO add * path with 404 not found page

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}
