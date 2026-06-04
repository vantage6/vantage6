import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class AuthRedirectService {
  private readonly INTENDED_URL_KEY = 'auth_intended_url';

  /**
   * Store the current URL as the intended redirect destination (for post-login)
   */
  setIntendedUrl(url: string): void {
    sessionStorage.setItem(this.INTENDED_URL_KEY, url);
  }

  /**
   * Get the stored intended URL and clear it
   */
  getAndClearIntendedUrl(): string | null {
    const url = sessionStorage.getItem(this.INTENDED_URL_KEY);
    sessionStorage.removeItem(this.INTENDED_URL_KEY);
    return url;
  }

  /**
   * Check if there's a stored intended URL
   */
  hasIntendedUrl(): boolean {
    return sessionStorage.getItem(this.INTENDED_URL_KEY) !== null;
  }

  /**
   * Clear the stored intended URL
   */
  clearIntendedUrl(): void {
    sessionStorage.removeItem(this.INTENDED_URL_KEY);
  }
}
