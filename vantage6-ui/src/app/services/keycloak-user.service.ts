import { Injectable } from '@angular/core';
import Keycloak from 'keycloak-js';

export interface KeycloakUserProfile {
  id?: string;
  username?: string;
  email?: string;
  firstName?: string;
  lastName?: string;
}

@Injectable({
  providedIn: 'root'
})
export class KeycloakUserService {
  private userProfile: KeycloakUserProfile | null = null;
  private isLoading = false;

  constructor(private keycloak: Keycloak) {
    this.init();
  }

  async init() {
    this.userProfile = await this.keycloak.loadUserProfile();
  }

  /**
   * Get the current user profile from Keycloak
   * @returns Promise<KeycloakUserProfile>
   */
  async getUserProfile(): Promise<KeycloakUserProfile | null> {
    if (this.userProfile) {
      return this.userProfile;
    } else {
      await this.init();
      return this.userProfile;
    }
  }

  /**
   * Clear the cached profile (useful after logout)
   */
  clearProfile(): void {
    this.userProfile = null;
  }
}
