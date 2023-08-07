import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { routePaths } from './routes';
import { LoginComponent } from './pages/login/login.component';
import { LayoutLoginComponent } from './layouts/layout-login/layout-login.component';
import { LayoutDefaultComponent } from './layouts/layout-default/layout-default.component';
import { HomeComponent } from './pages/home/home.component';
import { authenticationGuard } from './guards/authentication.guard';

const routes: Routes = [
  {
    path: routePaths.login,
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
        path: routePaths.home,
        component: HomeComponent,
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
