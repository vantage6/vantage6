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
        path: routerConfig.task,
        component: TaskReadComponent,
        canActivate: [authenticationGuard()]
      },
      {
        path: routerConfig.taskCreate,
        component: TaskCreateComponent,
        canActivate: [authenticationGuard()]
      },
      {
        path: routerConfig.tasks,
        component: TaskListComponent,
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
      }
    ]
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes, { bindToComponentInputs: true })],
  exports: [RouterModule]
})
export class AppRoutingModule {}
