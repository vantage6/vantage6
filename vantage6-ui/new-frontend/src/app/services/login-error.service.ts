import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class LoginErrorService {
  error: string | null = null;

  constructor() {}

  setError(error: string): void {
    this.error = error;
  }

  getError(): string {
    return this.error || '';
  }

  clearError(): void {
    this.error = null;
  }

  hasError(): boolean {
    return this.error !== null;
  }
}
