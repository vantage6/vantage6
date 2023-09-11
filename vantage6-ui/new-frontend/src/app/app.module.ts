import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { ReactiveFormsModule } from '@angular/forms';

import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
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
import { OrganizationComponent } from './pages/organization/organization.component';
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
    OrganizationComponent,
    TaskCreateComponent,
    StartComponent,
    TaskListComponent,
    TaskReadComponent,
    PageHeaderComponent,
    ChipComponent,
    AlertComponent,
    StatusInfoComponent,
    LogDialog,
    ConfirmDialog
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
    MatButtonModule,
    MatCardModule,
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
