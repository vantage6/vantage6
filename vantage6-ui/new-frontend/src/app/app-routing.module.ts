import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { routerConfig } from './routes';
import { LoginComponent } from './pages/login/login.component';
import { LayoutLoginComponent } from './layouts/layout-login/layout-login.component';
import { LayoutDefaultComponent } from './layouts/layout-default/layout-default.component';
import { HomeComponent } from './pages/home/home.component';
import { authenticationGuard } from './guards/authentication.guard';
import { OrganizationComponent } from './pages/organization/organization.component';
import { TaskComponent } from './pages/task/task.component';
import { StartComponent } from './pages/start/start.component';

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
        component: TaskComponent,
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
        component: OrganizationComponent,
        canActivate: [authenticationGuard()]
      }
    ]
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
