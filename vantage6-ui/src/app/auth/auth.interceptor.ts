import { Injectable } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor,
} from '@angular/common/http';
import { Observable } from 'rxjs';

import { TokenStorageService } from 'src/app/services/common/token-storage.service';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  constructor(public tokenStorage: TokenStorageService) {}

  // TODO include refresh token somehow

  intercept(
    request: HttpRequest<any>,
    next: HttpHandler
  ): Observable<HttpEvent<any>> {
    request = request.clone({
      setHeaders: {
        Authorization: `Bearer ${this.tokenStorage.getToken()}`,
      },
    });

    return next.handle(request);
  }
}
