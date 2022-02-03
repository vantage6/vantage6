import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { Operation, Resource, Scope } from './shared/enum';
import { AccessGuard, OrgAccessGuard } from 'src/app/auth/access-guard.guard';

import { LoginComponent } from './login/login.component';
import { HomeComponent } from './home/home.component';
import { OrganizationComponent } from './organization/organization.component';
import { UserEditComponent } from './user/user-edit/user-edit.component';
import { RoleEditComponent } from './role/role-edit/role-edit.component';
import { OrganizationEditComponent } from './organization/organization-edit/organization-edit.component';
import { CollaborationComponent } from './collaboration/collaboration.component';

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
      permissionType: Operation.CREATE,
      permissionResource: Resource.ORGANIZATION,
      permissionScope: Scope.GLOBAL,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'organization/create',
    component: OrganizationEditComponent,
    data: {
      requiresLogin: true,
      permissionType: Operation.CREATE,
      permissionResource: Resource.ORGANIZATION,
      permissionScope: Scope.GLOBAL,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'organization/:id',
    component: OrganizationComponent,
    data: {
      permissionType: Operation.VIEW,
    },
    canActivate: [OrgAccessGuard],
  },
  {
    path: 'organization/:id/edit',
    component: OrganizationEditComponent,
    data: {
      permissionType: Operation.EDIT,
    },
    canActivate: [OrgAccessGuard],
  },
  {
    path: 'user/create/:org_id',
    component: UserEditComponent,
    data: {
      requiresLogin: true,
      permissionType: Operation.CREATE,
      permissionResource: Resource.USER,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'user/:id/edit',
    component: UserEditComponent,
    data: {
      requiresLogin: true,
      permissionType: Operation.EDIT,
      permissionResource: Resource.USER,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'role/create/:org_id',
    component: RoleEditComponent,
    data: {
      requiresLogin: true,
      permissionType: Operation.CREATE,
      permissionResource: Resource.ROLE,
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'role/:id/edit',
    component: RoleEditComponent,
    data: {
      requiresLogin: true,
      permissionType: Operation.EDIT,
      permissionResource: Resource.ROLE,
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
