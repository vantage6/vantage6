import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClient, provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { OverlayModule } from '@angular/cdk/overlay';
import { QRCodeModule } from 'angularx-qrcode';

import { MAT_DATE_LOCALE } from '@angular/material/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
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
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatStepperModule } from '@angular/material/stepper';
import { MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTreeModule } from '@angular/material/tree';
import { MatDateFnsModule } from '@angular/material-date-fns-adapter';
import { MatRadioModule } from '@angular/material/radio';
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
import { OrganizationReadComponent } from './pages/admin/organization/read/organization-read.component';
import { TaskCreateComponent } from './pages/analyze/task/create/task-create.component';
import { ChooseCollaborationComponent } from './pages/analyze/choose-collaboration/choose-collaboration';
import { TaskListComponent } from './pages/analyze/task/list/task-list.component';
import { TaskReadComponent } from './pages/analyze/task/read/task-read.component';
import { PageHeaderComponent } from './components/page-header/page-header.component';
import { ChipComponent } from './components/helpers/chip/chip.component';
import { TreeDropdownComponent } from './components/helpers/tree-dropdown/tree-dropdown.component';
import { AlertComponent } from './components/alerts/alert/alert.component';
import { StatusInfoComponent } from './components/helpers/status-info/status-info.component';
import { LogDialogComponent } from './components/dialogs/log/log-dialog.component';
import { ConfirmDialogComponent } from './components/dialogs/confirm/confirm-dialog.component';
import { VisualizeResultComponent } from './components/visualization/visualize-result/visualize-result.component';
import { VisualizeTableComponent } from './components/visualization/visualize-table/visualize-table.component';
import { TableComponent } from './components/table/table.component';
import { CollaborationReadComponent } from './pages/admin/collaboration/read/collaboration-read.component';
import { CollaborationListComponent } from './pages/admin/collaboration/list/collaboration-list.component';
import { UserListComponent } from './pages/admin/user/list/user-list.component';
import { UserReadComponent } from './pages/admin/user/read/user-read.component';
import { OrganizationCreateComponent } from './pages/admin/organization/create/organization-create.component';
import { CollaborationCreateComponent } from './pages/admin/collaboration/create/collaboration-create.component';
import { UserCreateComponent } from './pages/admin/user/create/user-create.component';
import { OrganizationListComponent } from './pages/admin/organization/list/organization-list.component';
import { NodeReadComponent } from './pages/admin/node/read/node-read.component';
import { OrganizationEditComponent } from './pages/admin/organization/edit/organization-edit.component';
import { OrganizationFormComponent } from './components/forms/organization-form/organization-form.component';
import { CollaborationFormComponent } from './components/forms/collaboration-form/collaboration-form.component';
import { CollaborationEditComponent } from './pages/admin/collaboration/edit/collaboration-edit.component';
import { UserFormComponent } from './components/forms/user-form/user-form.component';
import { UserEditComponent } from './pages/admin/user/edit/user-edit.component';
import { VisualizeHistogramComponent } from './components/visualization/visualize-histogram/visualize-histogram.component';
import { PreprocessingStepComponent } from './pages/analyze/task/create/steps/preprocessing-step/preprocessing-step.component';
import { ChangePasswordComponent } from './pages/auth/change-password/change-password.component';
import { MessageDialogComponent } from './components/dialogs/message-dialog/message-dialog.component';
import { FilterStepComponent } from './pages/analyze/task/create/steps/filter-step/filter-step.component';
import { NumberOnlyDirective } from './directives/numberOnly.directive';
import { BreadcrumbsComponent } from './components/breadcrumbs/breadcrumbs.component';
import { TemplateTaskCreateComponent } from './pages/analyze/template-task/create/template-task-create.component';
import { DatabaseStepComponent } from './pages/analyze/task/create/steps/database-step/database-step.component';
import { RoleListComponent } from './pages/admin/role/list/role-list.component';
import { RoleReadComponent } from './pages/admin/role/read/role-read.component';
import { RoleCreateComponent } from './pages/admin/role/create/role-create.component';
import { RoleFormComponent } from './components/forms/role-form/role-form.component';
import { OrderByPipe } from './pipes/order-by.pipe';
import { SetupMfaComponent } from './pages/auth/setup-mfa/setup-mfa.component';
import { MfaCodeComponent } from './pages/auth/mfa-code/mfa-code.component';
import { MfaRecoverComponent } from './pages/auth/mfa-recover/mfa-recover.component';
import { MfaLostComponent } from './pages/auth/mfa-lost/mfa-lost.component';
import { AlertWithButtonComponent } from './components/alerts/alert-with-button/alert-with-button.component';
import { PasswordLostComponent } from './pages/auth/password-lost/password-lost.component';
import { PasswordRecoverComponent } from './pages/auth/password-recover/password-recover.component';
import { RoleSubmitButtonsComponent } from './components/helpers/role-submit-buttons/role-submit-buttons.component';
import { AddAlgoStoreComponent } from './pages/admin/collaboration/add-algo-store/add-algo-store.component';
import { AlgorithmStoreFormComponent } from './components/forms/algorithm-store-form/algorithm-store-form.component';
import { StudyReadComponent } from './pages/admin/collaboration/study/read/study-read.component';
import { StudyCreateComponent } from './pages/admin/collaboration/study/create/study-create.component';
import { StudyFormComponent } from './components/forms/study-form/study-form.component';
import { StudyEditComponent } from './pages/admin/collaboration/study/edit/study-edit.component';
import { AlgorithmListReadOnlyComponent } from './pages/analyze/algorithm/list/algorithm-list-read-only.component';
import { AlgorithmReadOnlyComponent } from './pages/analyze/algorithm/read-only/algorithm-read-only.component';
import { DisplayAlgorithmsComponent } from './components/algorithm/display-algorithms/display-algorithms.component';
import { AlgorithmStoreListComponent } from './pages/store/algorithm-stores/list/algorithm-store-list.component';
import { AlgorithmStoreReadComponent } from './pages/store/algorithm-stores/read/algorithm-store-read.component';
import { AlgorithmReadComponent } from './pages/store/algorithm/read/algorithm-read.component';
import { DisplayAlgorithmComponent } from './components/algorithm/display-algorithm/display-algorithm.component';
import { AlgorithmListComponent } from './pages/store/algorithm/list/algorithm-list.component';
import { AlgorithmCreateComponent } from './pages/store/algorithm/create/algorithm-create.component';
import { AlgorithmFormComponent } from './components/forms/algorithm-form/algorithm-form.component';
import { AlgorithmEditComponent } from './pages/store/algorithm/edit/algorithm-edit.component';
import { UploadPrivateKeyComponent } from './pages/analyze/choose-collaboration/upload-private-key/upload-private-key.component';
import { VisualizeLineComponent } from './components/visualization/visualize-line/visualize-line.component';
import { StoreUserListComponent } from './pages/store/user/list/store-user-list.component';
import { StoreUserReadComponent } from './pages/store/user/read/store-user-read.component';
import { StoreUserCreateComponent } from './pages/store/user/create/store-user-create.component';
import { StoreUserEditComponent } from './pages/store/user/edit/store-user-edit.component';
import { PermissionsMatrixServerComponent } from './components/permissions-matrix/server/permissions-matrix-server.component';
import { PermissionsMatrixStoreComponent } from './components/permissions-matrix/store/permissions-matrix-store.component';
import { StoreUserFormComponent } from './components/forms/store-user-form/store-user-form.component';
import { BaseCreateComponent } from './components/admin-base/base-create/base-create.component';
import { StoreRoleListComponent } from './pages/store/role/list/store-role-list.component';
import { StoreRoleReadComponent } from './pages/store/role/read/store-role-read.component';
import { AlgorithmInReviewListComponent } from './pages/store/algorithms-in-review/algorithm-in-review-list/algorithm-in-review-list.component';
import { AlgorithmAssignReviewComponent } from './pages/store/algorithms-in-review/algorithm-assign-review/algorithm-assign-review.component';
import { ReviewReadComponent } from './pages/store/algorithms-in-review/review-read/review-read.component';
import { ReviewSubmitComponent } from './pages/store/algorithms-in-review/review-submit/review-submit.component';
import { MyPendingAlgorithmsComponent } from './pages/store/algorithms-in-review/my-pending-algorithms/my-pending-algorithms.component';
import { OldAlgorithmListComponent } from './pages/store/algorithm/old-list/old-algorithm-list.component';
import { NodeAdminCardComponent } from './components/helpers/node-admin-card/node-admin-card.component';

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
    ChooseCollaborationComponent,
    TaskListComponent,
    TaskReadComponent,
    PageHeaderComponent,
    TreeDropdownComponent,
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
    RoleCreateComponent,
    RoleFormComponent,
    OrderByPipe,
    SetupMfaComponent,
    MfaCodeComponent,
    MfaRecoverComponent,
    MfaLostComponent,
    AlertWithButtonComponent,
    PasswordLostComponent,
    PasswordRecoverComponent,
    RoleSubmitButtonsComponent,
    AddAlgoStoreComponent,
    AlgorithmStoreFormComponent,
    StudyReadComponent,
    StudyCreateComponent,
    StudyFormComponent,
    StudyEditComponent,
    AlgorithmListReadOnlyComponent,
    AlgorithmReadOnlyComponent,
    DisplayAlgorithmsComponent,
    AlgorithmStoreListComponent,
    AlgorithmStoreReadComponent,
    AlgorithmReadComponent,
    DisplayAlgorithmComponent,
    AlgorithmListComponent,
    AlgorithmCreateComponent,
    AlgorithmFormComponent,
    AlgorithmEditComponent,
    UploadPrivateKeyComponent,
    VisualizeLineComponent,
    StoreUserListComponent,
    StoreUserReadComponent,
    StoreUserCreateComponent,
    StoreUserEditComponent,
    PermissionsMatrixServerComponent,
    PermissionsMatrixStoreComponent,
    StoreUserFormComponent,
    BaseCreateComponent,
    StoreRoleListComponent,
    StoreRoleReadComponent,
    AlgorithmInReviewListComponent,
    AlgorithmAssignReviewComponent,
    ReviewReadComponent,
    ReviewSubmitComponent,
    MyPendingAlgorithmsComponent,
    OldAlgorithmListComponent,
    NodeAdminCardComponent
  ],
  bootstrap: [AppComponent],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    AppRoutingModule,
    ReactiveFormsModule,
    FormsModule,
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
    MatChipsModule,
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
    MatSlideToggleModule,
    MatSnackBarModule,
    MatStepperModule,
    MatTabsModule,
    MatTableModule,
    MatToolbarModule,
    MatTreeModule,
    MatRadioModule,
    QRCodeModule,
    OverlayModule
  ],
  providers: [
    {
      provide: MAT_DATE_LOCALE,
      useValue: enCA
    },
    provideHttpClient(withInterceptorsFromDi())
  ]
})
export class AppModule { }
