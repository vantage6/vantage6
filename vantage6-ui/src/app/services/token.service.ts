import { Injectable, inject } from '@angular/core';
import { HttpInterceptorFn } from '@angular/common/http';
import Keycloak from 'keycloak-js';
import { from, switchMap } from 'rxjs';
import { environment } from 'src/environments/environment';
import { getUrlPattern } from '../helpers/regex.helper';

export const HQ_AUDIENCE_SCOPE = 'vantage6-hq-audience';
export const STORE_AUDIENCE_SCOPE = 'vantage6-store-audience';

// renew tokens this long before they expire
const RENEW_MARGIN_MS = 30_000;

/*
 * Provides the tokens for HQ and for algorithm stores.
 *
 * The user logs in for both, so the Keycloak token itself is valid at HQ and at
 * algorithm stores, and is never sent anywhere. Instead, its refresh token is used to
 * get a token that is only valid at HQ and one that is only valid at algorithm stores.
 */
@Injectable({
  providedIn: 'root'
})
export class TokenService {
  private readonly keycloak = inject(Keycloak);
  private readonly tokens = new Map<string, { token: string; expiresAt: number }>();
  private readonly requests = new Map<string, Promise<string | undefined>>();

  getHqToken(): Promise<string | undefined> {
    return this.getToken(HQ_AUDIENCE_SCOPE);
  }

  getStoreToken(): Promise<string | undefined> {
    return this.getToken(STORE_AUDIENCE_SCOPE);
  }

  private getToken(scope: string): Promise<string | undefined> {
    const cached = this.tokens.get(scope);
    if (cached && cached.expiresAt > Date.now() + RENEW_MARGIN_MS) {
      return Promise.resolve(cached.token);
    }
    // share one request between callers that need a new token at the same time
    let request = this.requests.get(scope);
    if (!request) {
      request = this.requestToken(scope).finally(() => this.requests.delete(scope));
      this.requests.set(scope, request);
    }
    return request;
  }

  private async requestToken(scope: string): Promise<string | undefined> {
    if (!this.keycloak.authenticated) {
      return undefined;
    }
    try {
      // renews the refresh token too, if the session is about to expire
      await this.keycloak.updateToken(RENEW_MARGIN_MS / 1000);
    } catch {
      return undefined;
    }
    const authUrl = environment.auth_url.replace(/\/$/, '');
    const realm = encodeURIComponent(environment.keycloak_realm);
    const response = await fetch(`${authUrl}/realms/${realm}/protocol/openid-connect/token`, {
      method: 'POST',
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        client_id: environment.keycloak_client,
        refresh_token: this.keycloak.refreshToken ?? '',
        scope: `openid ${scope}`
      })
    });
    if (!response.ok) {
      return undefined;
    }
    const body = await response.json();
    this.tokens.set(scope, { token: body.access_token, expiresAt: Date.now() + body.expires_in * 1000 });
    return body.access_token;
  }
}

const hqUrlPattern = getUrlPattern([environment.hq_url]);

/*
 * Adds the token for HQ to requests to HQ.
 */
export const hqTokenInterceptor: HttpInterceptorFn = (request, next) => {
  if (!hqUrlPattern.test(request.url)) {
    return next(request);
  }
  const tokenService = inject(TokenService);
  return from(tokenService.getHqToken()).pipe(
    switchMap((token) => next(token ? request.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : request))
  );
};
