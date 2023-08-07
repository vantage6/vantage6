import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, first } from 'rxjs';
import { ACCESS_TOKEN_KEY } from '../models/constants/sessionStorage';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  constructor(private http: HttpClient) {}

  async get<T = null>(url: string): Promise<T> {
    return await this.handleResult(
      this.http.get<T>(url, {
        headers: this.getAuthenticationHeaders()
      })
    );
  }

  async post<T = null>(url: string, body: any): Promise<T> {
    return await this.handleResult(
      this.http.post<T>(url, body, {
        headers: this.getAuthenticationHeaders()
      })
    );
  }

  private getAuthenticationHeaders(): any {
    const accessToken = sessionStorage.getItem(ACCESS_TOKEN_KEY);

    if (!accessToken) return {};

    return { Authorization: `Bearer ${accessToken}` };
  }

  private async handleResult<T = null>(request: Observable<T>): Promise<any> {
    return new Promise<T>((resolve, reject) => {
      request.pipe(first()).subscribe(
        (response) => {
          resolve(response as any);
        },
        (error) => {
          //TODO: handle error
          reject(error);
        }
      );
    });
  }
}
