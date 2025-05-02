import { MAT_DATE_LOCALE } from '@angular/material/core';
import { enCA } from 'date-fns/locale';
import { provideHttpClient, withInterceptorsFromDi, HttpClient } from '@angular/common/http';
import { DatePipe } from '@angular/common';
import { BrowserModule, bootstrapApplication } from '@angular/platform-browser';
import { provideAnimations } from '@angular/platform-browser/animations';
import { AppRoutingModule } from './app/app-routing.module';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { TranslateHttpLoader } from '@ngx-translate/http-loader';
import { MarkdownModule } from 'ngx-markdown';
import { MatDateFnsModule } from '@angular/material-date-fns-adapter';
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
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableModule } from '@angular/material/table';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTreeModule } from '@angular/material/tree';
import { MatRadioModule } from '@angular/material/radio';
import { MatTooltipModule } from '@angular/material/tooltip';
import { OverlayModule } from '@angular/cdk/overlay';
import { AppComponent } from './app/app.component';
import { importProvidersFrom } from '@angular/core';
import { provideKeycloakAngular } from './app/app.config';

export function HttpLoaderFactory(http: HttpClient) {
  return new TranslateHttpLoader(http, './assets/localizations/');
}

bootstrapApplication(AppComponent, {
  providers: [
    importProvidersFrom(
      BrowserModule,
      AppRoutingModule,
      ReactiveFormsModule,
      FormsModule,
      TranslateModule.forRoot({
        loader: { provide: TranslateLoader, useFactory: HttpLoaderFactory, deps: [HttpClient] },
        defaultLanguage: 'en'
      }),
      MarkdownModule.forRoot(),
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
      MatTooltipModule,
      OverlayModule
    ),
    { provide: MAT_DATE_LOCALE, useValue: enCA },
    provideHttpClient(withInterceptorsFromDi()),
    DatePipe,
    provideAnimations(),
    provideKeycloakAngular()
  ]
}).catch((err) => console.error(err));
