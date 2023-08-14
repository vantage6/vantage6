import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, first } from 'rxjs';
import { ACCESS_TOKEN_KEY } from '../models/constants/sessionStorage';
import { environment } from 'src/environments/environment.development';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  constructor(private http: HttpClient) {}

  async getForApi<T = null>(path: string): Promise<T> {
    return await this.handleResult(
      this.http.get<T>(environment.api_url + path, {
        headers: this.getApiAuthenticationHeaders()
      })
    );
  }

  async postForApi<T = null>(path: string, body: any): Promise<T> {
    return await this.handleResult(
      this.http.post<T>(environment.api_url + path, body, {
        headers: this.getApiAuthenticationHeaders()
      })
    );
  }

  async getForAlgorithmApi<T = null>(path: string): Promise<T> {
    return await this.handleResult(this.http.get<T>(environment.api_url + path));
  }

  private getApiAuthenticationHeaders(): any {
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
