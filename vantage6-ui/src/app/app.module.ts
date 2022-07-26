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
import { MatRadioModule } from '@angular/material/radio';
import { MatTableModule } from '@angular/material/table';
import { MatSortModule } from '@angular/material/sort';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatDividerModule } from '@angular/material/divider';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { NgbModule } from '@ng-bootstrap/ng-bootstrap';
import { CommonModule } from '@angular/common';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { LoginComponent } from './components/login/login.component';
import { HomeComponent } from './components/home/home.component';
import {
  AccessGuard,
  AccessGuardByOrgId,
  OrgAccessGuard,
} from './auth/access-guard.guard';
import { NavbarComponent } from './components/navbar/navbar.component';
import { OrganizationComponent } from './components/organization/organization.component';
import { AuthInterceptor } from './auth/auth.interceptor';
import { PermissionTableComponent } from './components/permission-table/permission-table.component';
import { UserEditComponent } from './components/edit/user-edit/user-edit.component';
import { UserViewComponent } from './components/view/user-view/user-view.component';
import { RoleViewComponent } from './components/view/role-view/role-view.component';
import { RoleEditComponent } from './components/edit/role-edit/role-edit.component';
import { ModalDeleteComponent } from './components/modal/modal-delete/modal-delete.component';
import { ModalMessageComponent } from './components/modal/modal-message/modal-message.component';
import { OrganizationEditComponent } from './components/edit/organization-edit/organization-edit.component';
import { CollaborationViewComponent } from './components/view/collaboration-view/collaboration-view.component';
import { NodeViewComponent } from './components/view/node-view/node-view.component';
import { ModalEditComponent } from './components/modal/modal-edit/modal-edit.component';
import { CollaborationEditComponent } from './components/edit/collaboration-edit/collaboration-edit.component';
import { RoleTableComponent } from './components/table/role-table/role-table.component';
import { CdkDetailRowDirective } from './components/table/base-table/cdk-detail-row-directive';
import { UserTableComponent } from './components/table/user-table/user-table.component';
import { NodeTableComponent } from './components/table/node-table/node-table.component';
import { CollaborationViewSingleComponent } from './components/view-single/collaboration-view-single/collaboration-view-single.component';
import { MatFormFieldModule } from '@angular/material/form-field';
import { TaskTableComponent } from './components/table/task-table/task-table.component';
import { TaskViewComponent } from './components/view/task-view/task-view.component';
import { TaskViewSingleComponent } from './components/view-single/task-view-single/task-view-single.component';
import { ResultViewComponent } from './components/view/result-view/result-view.component';
import { ProfileComponent } from './components/profile/profile.component';
import { CollaborationTableComponent } from './components/table/collaboration-table/collaboration-table.component';
import { RoleViewSingleComponent } from './components/view-single/role-view-single/role-view-single.component';
import { UserViewSingleComponent } from './components/view-single/user-view-single/user-view-single.component';
import { NodeSingleViewComponent } from './components/view-single/node-single-view/node-single-view.component';
import { ModalLoadingComponent } from './components/modal/modal-loading/modal-loading.component';

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
    CollaborationViewComponent,
    NodeViewComponent,
    ModalEditComponent,
    CollaborationEditComponent,
    RoleTableComponent,
    CdkDetailRowDirective,
    UserTableComponent,
    NodeTableComponent,
    CollaborationViewSingleComponent,
    TaskTableComponent,
    TaskViewComponent,
    TaskViewSingleComponent,
    ResultViewComponent,
    ProfileComponent,
    CollaborationTableComponent,
    RoleViewSingleComponent,
    UserViewSingleComponent,
    NodeSingleViewComponent,
    ModalLoadingComponent,
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
    MatRadioModule,
    MatCheckboxModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    CommonModule,
    NgbModule,
  ],
  providers: [
    AccessGuard,
    OrgAccessGuard,
    AccessGuardByOrgId,
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true,
    },
  ],
  bootstrap: [AppComponent],
})
export class AppModule {}
