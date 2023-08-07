import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, first } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  constructor(private http: HttpClient) {}

  async get<T = null>(url: string): Promise<T> {
    return await this.handleResult(this.http.get<T>(url));
  }

  async post<T = null>(url: string, body: any): Promise<T> {
    return await this.handleResult(this.http.post<T>(url, body));
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
