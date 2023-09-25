import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { routerConfig } from './routes';
import { LoginComponent } from './pages/login/login.component';
import { LayoutLoginComponent } from './layouts/layout-login/layout-login.component';
import { LayoutDefaultComponent } from './layouts/layout-default/layout-default.component';
import { HomeComponent } from './pages/home/home.component';
import { authenticationGuard } from './guards/authentication.guard';
import { OrganizationReadComponent } from './pages/organization/read/organization-read.component';
import { TaskCreateComponent } from './pages/task/create/task-create.component';
import { StartComponent } from './pages/start/start.component';
import { TaskListComponent } from './pages/task/list/task-list.component';
import { TaskReadComponent } from './pages/task/read/task-read.component';
import { CollaborationReadComponent } from './pages/collaboration/read/collaboration-read.component';
import { CollaborationListComponent } from './pages/collaboration/list/collaboration-list.component';
import { UserListComponent } from './pages/user/list/user-list.component';
import { UserReadComponent } from './pages/user/read/user-read.component';
import { OrganizationCreateComponent } from './pages/organization/create/organization-create.component';
import { CollaborationCreateComponent } from './pages/collaboration/create/collaboration-create.component';

const routes: Routes = [
  {
    path: routerConfig.login,
    component: LayoutLoginComponent,
    children: [
      {
        path: '',
        component: LoginComponent
      }
    ]
  },
  {
    path: '',
    component: LayoutDefaultComponent,
    children: [
      {
        path: routerConfig.start,
        component: StartComponent,
        canActivate: [authenticationGuard()]
      },
      {
        path: routerConfig.home,
        component: HomeComponent,
        canActivate: [authenticationGuard()]
      },
      {
        path: routerConfig.tasks,
        component: TaskListComponent,
        canActivate: [authenticationGuard()]
      },
      {
        path: routerConfig.taskCreate,
        component: TaskCreateComponent,
        canActivate: [authenticationGuard()]
      },
      {
        path: routerConfig.task,
        component: TaskReadComponent,
        canActivate: [authenticationGuard()]
      }
    ]
  },
  {
    path: routerConfig.admin,
    component: LayoutDefaultComponent,
    children: [
      {
        path: routerConfig.adminHome,
        component: HomeComponent,
        canActivate: [authenticationGuard()]
      },
      {
        path: routerConfig.organization,
        component: OrganizationReadComponent,
        canActivate: [authenticationGuard()]
      },
      {
        path: routerConfig.organizationCreate,
        component: OrganizationCreateComponent,
        canActivate: [authenticationGuard()]
      },
      {
        path: routerConfig.collaborations,
        component: CollaborationListComponent,
        canActivate: [authenticationGuard()]
      },
      {
        path: routerConfig.collaborationCreate,
        component: CollaborationCreateComponent,
        canActivate: [authenticationGuard()]
      },
      {
        path: routerConfig.collaboration,
        component: CollaborationReadComponent,
        canActivate: [authenticationGuard()]
      },
      {
        path: routerConfig.users,
        component: UserListComponent,
        canActivate: [authenticationGuard()]
      },
      {
        path: routerConfig.user,
        component: UserReadComponent,
        canActivate: [authenticationGuard()]
      }
    ]
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes, { bindToComponentInputs: true })],
  exports: [RouterModule]
})
export class AppRoutingModule {}
