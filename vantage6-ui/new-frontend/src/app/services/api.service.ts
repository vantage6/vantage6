import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, first } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  constructor(private http: HttpClient) {}

  post = async (url: string, body: any): Promise<any> => {
    return await this.handleResult(this.http.post(url, body));
  };

  private async handleResult(request: Observable<any>): Promise<any> {
    return new Promise<any>((resolve, reject) => {
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
