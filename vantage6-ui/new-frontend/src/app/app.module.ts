import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { ReactiveFormsModule } from '@angular/forms';
import { QRCodeModule } from 'angularx-qrcode';

import { MAT_DATE_LOCALE } from '@angular/material/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatDialogModule } from '@angular/material/dialog';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatMenuModule } from '@angular/material/menu';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatStepperModule } from '@angular/material/stepper';
import { MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatDateFnsModule } from '@angular/material-date-fns-adapter';
import { enCA } from 'date-fns/locale';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { LoginComponent } from './pages/auth/login/login.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { TranslateLoader, TranslateModule } from '@ngx-translate/core';
import { TranslateHttpLoader } from '@ngx-translate/http-loader';
import { LayoutLoginComponent } from './layouts/layout-login/layout-login.component';
import { HomeComponent } from './pages/home/home.component';
import { LayoutDefaultComponent } from './layouts/layout-default/layout-default.component';
import { OrganizationReadComponent } from './pages/organization/read/organization-read.component';
import { TaskCreateComponent } from './pages/task/create/task-create.component';
import { StartComponent } from './pages/start/start.component';
import { TaskListComponent } from './pages/task/list/task-list.component';
import { TaskReadComponent } from './pages/task/read/task-read.component';
import { PageHeaderComponent } from './components/page-header/page-header.component';
import { ChipComponent } from './components/chip/chip.component';
import { AlertComponent } from './components/alert/alert.component';
import { StatusInfoComponent } from './components/status-info/status-info.component';
import { LogDialogComponent } from './components/dialogs/log/log-dialog.component';
import { ConfirmDialogComponent } from './components/dialogs/confirm/confirm-dialog.component';
import { VisualizeResultComponent } from './components/visualize-result/visualize-result.component';
import { VisualizeTableComponent } from './components/visualize-table/visualize-table.component';
import { TableComponent } from './components/table/table.component';
import { CollaborationReadComponent } from './pages/collaboration/read/collaboration-read.component';
import { CollaborationListComponent } from './pages/collaboration/list/collaboration-list.component';
import { UserListComponent } from './pages/user/list/user-list.component';
import { UserReadComponent } from './pages/user/read/user-read.component';
import { OrganizationCreateComponent } from './pages/organization/create/organization-create.component';
import { CollaborationCreateComponent } from './pages/collaboration/create/collaboration-create.component';
import { UserCreateComponent } from './pages/user/create/user-create.component';
import { OrganizationListComponent } from './pages/organization/list/organization-list.component';
import { NodeReadComponent } from './pages/node/read/node-read.component';
import { OrganizationEditComponent } from './pages/organization/edit/organization-edit.component';
import { OrganizationFormComponent } from './components/forms/organization-form/organization-form.component';
import { CollaborationFormComponent } from './components/forms/collaboration-form/collaboration-form.component';
import { CollaborationEditComponent } from './pages/collaboration/edit/collaboration-edit.component';
import { UserFormComponent } from './components/forms/user-form/user-form.component';
import { UserEditComponent } from './pages/user/edit/user-edit.component';
import { VisualizeHistogramComponent } from './components/visualize-histogram/visualize-histogram.component';
import { PreprocessingStepComponent } from './pages/task/create/steps/preprocessing-step/preprocessing-step.component';
import { ChangePasswordComponent } from './pages/auth/change-password/change-password.component';
import { MessageDialogComponent } from './components/dialogs/message-dialog/message-dialog.component';
import { FilterStepComponent } from './pages/task/create/steps/filter-step/filter-step.component';
import { NumberOnlyDirective } from './directives/numberOnly.directive';
import { BreadcrumbsComponent } from './components/breadcrumbs/breadcrumbs.component';
import { TemplateTaskCreateComponent } from './pages/template-task/create/template-task-create.component';
import { DatabaseStepComponent } from './pages/task/create/steps/database-step/database-step.component';
import { RoleListComponent } from './pages/role/list/role-list.component';
import { RoleReadComponent } from './pages/role/read/role-read.component';
import { RoleCreateComponent } from './pages/role/create/role-create.component';
import { PermissionsMatrixComponent } from './components/permissions-matrix/permissions-matrix.component';
import { RoleFormComponent } from './components/role-form/role-form.component';
import { OrderByPipe } from './pipes/order-by.pipe';
import { SetupMfaComponent } from './pages/auth/setup-mfa/setup-mfa.component';
import { MfaCodeComponent } from './pages/auth/mfa-code/mfa-code.component';
import { MfaRecoverComponent } from './pages/auth/mfa-recover/mfa-recover.component';
import { MfaLostComponent } from './pages/auth/mfa-lost/mfa-lost.component';
import { AlertWithButtonComponent } from './components/alert-with-button/alert-with-button.component';
import { PasswordLostComponent } from './pages/auth/password-lost/password-lost.component';
import { PasswordRecoverComponent } from './pages/auth/password-recover/password-recover.component';

export function HttpLoaderFactory(http: HttpClient) {
  return new TranslateHttpLoader(http, './assets/localizations/');
}

@NgModule({
  declarations: [
    AppComponent,
    LayoutLoginComponent,
    LoginComponent,
    HomeComponent,
    LayoutDefaultComponent,
    OrganizationListComponent,
    OrganizationCreateComponent,
    OrganizationReadComponent,
    TaskCreateComponent,
    StartComponent,
    TaskListComponent,
    TaskReadComponent,
    PageHeaderComponent,
    ChipComponent,
    AlertComponent,
    StatusInfoComponent,
    LogDialogComponent,
    ConfirmDialogComponent,
    VisualizeResultComponent,
    VisualizeTableComponent,
    TableComponent,
    CollaborationReadComponent,
    CollaborationListComponent,
    UserListComponent,
    UserReadComponent,
    CollaborationCreateComponent,
    UserCreateComponent,
    NodeReadComponent,
    OrganizationEditComponent,
    OrganizationFormComponent,
    CollaborationFormComponent,
    CollaborationEditComponent,
    UserFormComponent,
    UserEditComponent,
    VisualizeHistogramComponent,
    PreprocessingStepComponent,
    ChangePasswordComponent,
    MessageDialogComponent,
    FilterStepComponent,
    NumberOnlyDirective,
    BreadcrumbsComponent,
    TemplateTaskCreateComponent,
    DatabaseStepComponent,
    RoleListComponent,
    RoleReadComponent,
    PermissionsMatrixComponent,
    RoleCreateComponent,
    RoleFormComponent,
    OrderByPipe
    SetupMfaComponent,
    MfaCodeComponent,
    MfaRecoverComponent,
    MfaLostComponent,
    AlertWithButtonComponent,
    PasswordLostComponent,
    PasswordRecoverComponent
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    AppRoutingModule,
    HttpClientModule,
    ReactiveFormsModule,
    TranslateModule.forRoot({
      loader: {
        provide: TranslateLoader,
        useFactory: HttpLoaderFactory,
        deps: [HttpClient]
      },
      defaultLanguage: 'en'
    }),
    MatDateFnsModule,
    MatButtonModule,
    MatCardModule,
    MatCheckboxModule,
    MatDatepickerModule,
    MatDialogModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatListModule,
    MatMenuModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSidenavModule,
    MatSnackBarModule,
    MatStepperModule,
    MatTabsModule,
    MatTableModule,
    MatToolbarModule,
    QRCodeModule
  ],
  providers: [
    {
      provide: MAT_DATE_LOCALE,
      useValue: enCA
    }
  ],
  bootstrap: [AppComponent]
})
export class AppModule {}
