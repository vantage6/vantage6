import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { ReactiveFormsModule } from '@angular/forms';

import { MatNativeDateModule } from '@angular/material/core';
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
import { MatStepperModule } from '@angular/material/stepper';
import { MatTableModule } from '@angular/material/table';
import { MatToolbarModule } from '@angular/material/toolbar';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { LoginComponent } from './pages/login/login.component';
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
import { LogDialog } from './components/dialogs/log/log-dialog.component';
import { ConfirmDialog } from './components/dialogs/confirm/confirm-dialog.component';
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
import { OrganizationFormComponent } from './components/organization-form/organization-form/organization-form.component';
import { CollaborationFormComponent } from './components/collaboration-form/collaboration-form.component';
import { CollaborationEditComponent } from './pages/collaboration/edit/collaboration-edit.component';
import { UserFormComponent } from './components/user-form/user-form/user-form.component';
import { UserEditComponent } from './pages/user/edit/user-edit.component';
import { VisualizeHistogramComponent } from './components/visualize-histogram/visualize-histogram.component';
import { PreprocessingStepComponent } from './pages/task/create/steps/preprocessing-step/preprocessing-step.component';
import { ChangePasswordComponent } from './pages/change-password/change-password.component';
import { MessageDialog } from './components/dialogs/message-dialog/message-dialog.component';

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
    LogDialog,
    ConfirmDialog,
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
    MessageDialog
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
    MatNativeDateModule,
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
    MatStepperModule,
    MatTableModule,
    MatToolbarModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule {}
