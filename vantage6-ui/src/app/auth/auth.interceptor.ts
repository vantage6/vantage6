import {
  HttpClient,
  HttpErrorResponse,
  HttpHandler,
  HttpInterceptor,
  HttpRequest,
} from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of, throwError } from 'rxjs';
import { catchError, filter, switchMap, take, tap } from 'rxjs/operators';

import { TokenStorageService } from 'src/app/services/common/token-storage.service';
import { environment } from 'src/environments/environment';
import { SignOutService } from '../services/common/sign-out.service';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  private isRefreshing = false;
  private refreshTokenSubject: BehaviorSubject<any> = new BehaviorSubject<any>(
    null
  );

  constructor(
    private http: HttpClient,
    private tokenStorage: TokenStorageService,
    private signOutService: SignOutService
  ) {}

  intercept(request: HttpRequest<any>, next: HttpHandler): Observable<any> {
    const token = this.tokenStorage.getToken();
    if (token) {
      request = this.addToken(request, token);
    }

    return next.handle(request).pipe(
      catchError((error) => {
        if (error instanceof HttpErrorResponse && error.status === 401) {
          // if there is a 401 error, try token refresh. Unless the token
          // refresh already returned a 401, in which case we need to logout
          if (request.url === `${environment.api_url}/token/refresh`) {
            this.signOutService.signOut();
            return of(true);
          } else {
            return this.handle401Error(request, next);
          }
        } else {
          return throwError(error);
        }
      })
    );
  }

  private addToken(request: HttpRequest<any>, token: string) {
    return request.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  private handle401Error(request: HttpRequest<any>, next: HttpHandler) {
    if (!this.isRefreshing) {
      this.isRefreshing = true;
      // clear current token: no longer valid
      this.refreshTokenSubject.next(null);
      this.tokenStorage.deleteToken();

      return this.refreshToken().pipe(
        switchMap((token: any) => {
          this.isRefreshing = false;
          this.refreshTokenSubject.next(token.access_token);
          return next.handle(this.addToken(request, token.access_token));
        })
      );
    } else {
      // token refresh is in progress, wait for it to complete and take new
      // token. No need to log out user here: if refreshing token fails, user
      // will be logged out in refresh token function
      return this.refreshTokenSubject.pipe(
        filter((token) => token != null),
        take(1),
        switchMap((jwt) => {
          return next.handle(this.addToken(request, jwt));
        })
      );
    }
  }

  refreshToken() {
    return this.http
      .post<any>(
        `${environment.api_url}/token/refresh`,
        {},
        {
          headers: {
            Authorization: `Bearer ${this.tokenStorage.getRefreshToken()}`,
          },
        }
      )
      .pipe(
        tap((token) => {
          this.tokenStorage.setLoginData(token);
        })
      );
  }
}
