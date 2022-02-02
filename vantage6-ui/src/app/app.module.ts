import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatDividerModule } from '@angular/material/divider';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { NgbModule } from '@ng-bootstrap/ng-bootstrap';
import { CommonModule } from '@angular/common';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { LoginComponent } from './login/login.component';
import { HomeComponent } from './home/home.component';
import { AccessGuard, OrgAccessGuard } from './auth/access-guard.guard';
import { NavbarComponent } from './navbar/navbar.component';
import { OrganizationComponent } from './organization/organization.component';
import { AuthInterceptor } from './auth/auth.interceptor';
import { PermissionTableComponent } from './shared/permission-table/permission-table.component';
import { UserEditComponent } from './user/user-edit/user-edit.component';
import { UserViewComponent } from './user/user-view/user-view.component';
import { RoleViewComponent } from './role/role-view/role-view.component';
import { RoleEditComponent } from './role/role-edit/role-edit.component';
import { ModalDeleteComponent } from './modal/modal-delete/modal-delete.component';
import { ModalMessageComponent } from './modal/modal-message/modal-message.component';
import { OrganizationEditComponent } from './organization/organization-edit/organization-edit.component';

@NgModule({
  declarations: [
    AppComponent,
    LoginComponent,
    HomeComponent,
    NavbarComponent,
    OrganizationComponent,
    PermissionTableComponent,
    UserEditComponent,
    UserViewComponent,
    RoleViewComponent,
    RoleEditComponent,
    ModalDeleteComponent,
    ModalMessageComponent,
    OrganizationEditComponent,
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    FormsModule,
    HttpClientModule,
    NoopAnimationsModule,
    BrowserAnimationsModule,
    MatToolbarModule,
    MatSidenavModule,
    MatButtonModule,
    MatIconModule,
    MatDividerModule,
    MatCardModule,
    MatExpansionModule,
    CommonModule,
    NgbModule,
  ],
  providers: [
    AccessGuard,
    OrgAccessGuard,
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true,
    },
  ],
  bootstrap: [AppComponent],
})
export class AppModule {}
