import { Injectable } from '@angular/core';
import Keycloak from 'keycloak-js';
import { environment } from 'src/environments/environment';
import { getUrlPattern } from 'src/app/helpers/regex.helper';

/*
 * Provides the token for algorithm stores.
 *
 * Algorithm stores get a separate token from a separate Keycloak client, which HQ does
 * not accept. The user is already logged in to Keycloak, so this logs in silently.
 */
@Injectable({
  providedIn: 'root'
})
export class StoreAuthService {
  private readonly keycloak = new Keycloak({
    realm: environment.keycloak_realm,
    url: environment.auth_url,
    clientId: environment.keycloak_store_client
  });
  private initialized: Promise<boolean> | null = null;
  private readonly allowedStorePattern = getAllowedStorePattern();

  async getToken(storeUrl: string): Promise<string | undefined> {
    if (!this.allowedStorePattern.test(storeUrl)) {
      return undefined;
    }
    if (!this.initialized) {
      this.initialized = this.keycloak
        .init({
          onLoad: 'check-sso',
          silentCheckSsoRedirectUri: window.location.origin + '/silent-check-sso.html'
        })
        .catch(() => false);
    }
    if (!(await this.initialized)) {
      return undefined;
    }
    try {
      await this.keycloak.updateToken(30);
    } catch {
      return undefined;
    }
    return this.keycloak.token;
  }
}

/*
 * Pattern of the algorithm store URLs that may receive the store token. If the allowed
 * algorithm stores is '*', all stores may receive it.
 */
function getAllowedStorePattern(): RegExp {
  if (environment.allowed_algorithm_stores === '*') {
    return new RegExp(`.*`, 'i');
  }
  return getUrlPattern(environment.allowed_algorithm_stores.split(' '));
}
