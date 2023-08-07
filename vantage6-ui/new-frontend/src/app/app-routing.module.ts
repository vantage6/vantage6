import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { routePaths } from './routes';
import { LoginComponent } from './pages/login/login.component';
import { LayoutLoginComponent } from './layouts/layout-login/layout-login.component';

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
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
