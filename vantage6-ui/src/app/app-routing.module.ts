import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { LoginComponent } from './login/login.component';
import { HomeComponent } from './home/home.component';
import { AccessGuard, OrgAccessGuard } from './access-guard.guard';
import { OrganizationComponent } from './organization/organization.component';
import { UserEditComponent } from './user/user-edit/user-edit.component';
import { RoleEditComponent } from './role/role-edit/role-edit.component';
import { OrganizationEditComponent } from './organization/organization-edit/organization-edit.component';

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
    path: 'organization/create',
    component: OrganizationEditComponent,
    data: {
      requiresLogin: true,
      permissionType: 'create',
      permissionResource: 'organization',
      permissionScope: 'global',
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'organization/:id',
    component: OrganizationComponent,
    data: {
      permissionType: 'view',
    },
    canActivate: [OrgAccessGuard],
  },
  {
    path: 'organization/:id/edit',
    component: OrganizationEditComponent,
    data: {
      permissionType: 'edit',
    },
    canActivate: [OrgAccessGuard],
  },
  {
    path: 'user/create',
    component: UserEditComponent,
    data: {
      requiresLogin: true,
      permissionType: 'create',
      permissionResource: 'user',
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'user/:id/edit',
    component: UserEditComponent,
    data: {
      requiresLogin: true,
      permissionType: 'edit',
      permissionResource: 'user',
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'role/:id/edit',
    component: RoleEditComponent,
    data: {
      requiresLogin: true,
      permissionType: 'edit',
      permissionResource: 'role',
    },
    canActivate: [AccessGuard],
  },
  {
    path: 'role/create',
    component: RoleEditComponent,
    data: {
      requiresLogin: true,
      permissionType: 'create',
      permissionResource: 'role',
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
