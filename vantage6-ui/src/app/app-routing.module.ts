import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { OpsType, ResType, ScopeType } from './shared/enum';
import {
  AccessGuard,
  AccessGuardByOrgId,
  OrgAccessGuard,
} from 'src/app/auth/access-guard.guard';

import { LoginComponent } from './components/login/login.component';
import { HomeComponent } from './components/home/home.component';
import { OrganizationComponent } from './components/organization/organization.component';
import { UserEditComponent } from './components/user/user-edit/user-edit.component';
import { RoleEditComponent } from './components/role/role-edit/role-edit.component';
import { OrganizationEditComponent } from './components/organization/organization-edit/organization-edit.component';
import { CollaborationComponent } from './components/collaboration/collaboration.component';
import { NodeViewComponent } from './components/node/node-view/node-view.component';
import { CollaborationEditComponent } from './components/collaboration/collaboration-edit/collaboration-edit.component';
import { RoleTableComponent } from './components/role/role-table/role-table.component';
import { UserTableComponent } from './components/user/user-table/user-table.component';
import { NodeTableComponent } from './components/node/node-table/node-table.component';
import { CollaborationViewSingleComponent } from './components/collaboration/collaboration-view-single/collaboration-view-single.component';

const routes: Routes = [
  {
    path: 'login',
    component: LoginComponent,
  },
  {
    path: 'home',
    component: HomeComponent,
    data: { requiresLogin: true },
    canActivate: [AccessGuard],
  },
  { path: '', redirectTo: '/home', pathMatch: 'full' },
  {
    path: 'collaboration',
    component: CollaborationComponent,
    data: {
      requiresLogin: true,
      permissionType: OpsType.VIEW,
      permissionResource: ResType.COLLABORATION,
    },
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
    component: NodeViewComponent,
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
];
//TODO add * path with 404 not found page

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}
