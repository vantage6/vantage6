import { ApplicationConfig, provideZoneChangeDetection, importProvidersFrom } from '@angular/core';
import { MAT_DATE_LOCALE } from '@angular/material/core';
import { enCA } from 'date-fns/locale';
import { provideHttpClient, withInterceptorsFromDi, HttpClient, withInterceptors } from '@angular/common/http';
import { DatePipe } from '@angular/common';
import { BrowserModule } from '@angular/platform-browser';
import { provideAnimations } from '@angular/platform-browser/animations';
import { AppRoutingModule } from './app-routing.module';
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
import { provideRouter } from '@angular/router';
import { routes } from './app-routing.module';

import {
  provideKeycloak,
  createInterceptorCondition,
  IncludeBearerTokenCondition,
  INCLUDE_BEARER_TOKEN_INTERCEPTOR_CONFIG,
  withAutoRefreshToken,
  AutoRefreshTokenService,
  UserActivityService,
  includeBearerTokenInterceptor
} from 'keycloak-angular';
import { environment } from 'src/environments/environment';

/*
 * Get the URL pattern for services that the token is sent to.

 * If the allowed algorithm stores is '*', return a pattern that matches all URLs.
 * If allowed algorithm stores are specified, we can determine the URL pattern to allow
 * for the Bearer token inclusion as thes server URL plus the allowed algorithm stores.
 */
function getUrlPattern() {
  if (environment.allowed_algorithm_stores === '*') {
    return new RegExp(`.*`, 'i');
  }
  const urls: string[] = environment.allowed_algorithm_stores.split(' ');
  urls.push(environment.server_url);

  // Create a pattern that matches the base URL and any subpaths
  // Escape special regex characters in URLs and add optional trailing slash and subpaths
  const escapedUrls = urls.map((url) => {
    const escaped = url.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return `${escaped}(/.*)?`;
  });
  return new RegExp(`^(${escapedUrls.join('|')})$`, 'i');
}

// Send the Keycloak token along with requests when the user is authenticated. The url
// pattern defines to which backend services the token is included.
const UrlCondition = createInterceptorCondition<IncludeBearerTokenCondition>({
  urlPattern: getUrlPattern(),
  bearerPrefix: 'Bearer'
});

export const provideKeycloakAngular = () =>
  provideKeycloak({
    config: {
      realm: environment.keycloak_realm,
      url: environment.auth_url,
      clientId: environment.keycloak_client
    },
    initOptions: {
      onLoad: 'check-sso',
      // checkLoginIframe: true
      silentCheckSsoRedirectUri: window.location.origin + '/silent-check-sso.html',
      redirectUri: window.location.origin + '/'
    },
    features: [
      withAutoRefreshToken({
        onInactivityTimeout: 'logout',
        sessionTimeout: Number(environment.refresh_token_validity_seconds) * 1000
      })
    ],
    providers: [
      AutoRefreshTokenService,
      UserActivityService,
      {
        provide: INCLUDE_BEARER_TOKEN_INTERCEPTOR_CONFIG,
        useValue: [UrlCondition]
      }
    ]
  });

export function HttpLoaderFactory(http: HttpClient) {
  return new TranslateHttpLoader(http, './assets/localizations/');
}

export const appConfig: ApplicationConfig = {
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
    provideHttpClient(withInterceptorsFromDi(), withInterceptors([includeBearerTokenInterceptor])),
    DatePipe,
    provideAnimations(),
    provideKeycloakAngular(),
    provideRouter(routes),
    provideZoneChangeDetection({ eventCoalescing: true })
  ]
};
