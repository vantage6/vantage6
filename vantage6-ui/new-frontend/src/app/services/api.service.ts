import { HttpClient, HttpResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, first } from 'rxjs';
import { ACCESS_TOKEN_KEY } from '../models/constants/sessionStorage';
import { environment } from 'src/environments/environment.development';
import { Pagination } from '../models/api/pagination.model';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  constructor(private http: HttpClient) {}

  async getForApi<T = null>(path: string, params: object | null = null): Promise<T> {
    return await this.handleResult(
      this.http.get<T>(this.getApiPath(path), {
        headers: this.getApiAuthenticationHeaders(),
        params: { ...params }
      })
    );
  }

  async getForApiWithPagination<T>(path: string, currentPage: number, parameters: object | null = null): Promise<Pagination<T>> {
    return await this.handleResultForPagination(
      this.http.get<Pagination<T>>(this.getApiPath(path), {
        headers: this.getApiAuthenticationHeaders(),
        observe: 'response',
        params: {
          ...parameters,
          page: currentPage,
          per_page: '10'
        }
      })
    );
  }

  async postForApi<T>(path: string, body: any): Promise<T> {
    return await this.handleResult(
      this.http.post<T>(this.getApiPath(path), body, {
        headers: this.getApiAuthenticationHeaders()
      })
    );
  }

  async patchForApi<T>(path: string, body: any): Promise<T> {
    return await this.handleResult(
      this.http.patch<T>(this.getApiPath(path), body, {
        headers: this.getApiAuthenticationHeaders()
      })
    );
  }

  async deleteForApi(path: string): Promise<any> {
    return await this.handleResult(
      this.http.delete(this.getApiPath(path), {
        headers: this.getApiAuthenticationHeaders()
      })
    );
  }

  async getForAlgorithmApi<T = null>(path: string): Promise<T> {
    return await this.handleResult(this.http.get<T>(environment.algorithm_server_url + path));
  }

  private getApiAuthenticationHeaders(): any {
    const accessToken = sessionStorage.getItem(ACCESS_TOKEN_KEY);

    if (!accessToken) return {};

    return { Authorization: `Bearer ${accessToken}` };
  }

  private async handleResult<T = null>(request: Observable<T>): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      request.pipe(first()).subscribe(
        (response) => {
          resolve(response as T);
        },
        (error) => {
          //TODO: handle error
          console.log(error.error?.msg ? error.error?.msg : 'A error occurred');
          reject(error);
        }
      );
    });
  }

  private async handleResultForPagination<T>(request: Observable<HttpResponse<Pagination<T>>>): Promise<Pagination<T>> {
    return new Promise<any>((resolve, reject) => {
      request.pipe(first()).subscribe(
        (response) => {
          const body = response.body as Pagination<T>;

          if (body.links) {
            body.links['total'] = Number.parseInt(response.headers.get('Total-Count') || '0');
          }
          resolve(body);
        },
        (error) => {
          //TODO: handle error
          console.log(error.msg ? error.msg : 'A error occurred');
          reject(error);
        }
      );
    });
  }

  private getApiPath(path: string): string {
    //TODO: Lazy loaded calls already include API path
    if (path.startsWith('/') && path.startsWith(environment.api_path)) {
      return environment.server_url + path;
    }
    return environment.server_url + environment.api_path + path;
  }
}
