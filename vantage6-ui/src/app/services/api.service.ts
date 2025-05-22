import { HttpClient, HttpErrorResponse, HttpResponse, HttpStatusCode } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, first } from 'rxjs';
import { ACCESS_TOKEN_KEY } from 'src/app/models/constants/sessionStorage';
import { environment } from 'src/environments/environment';
import { Pagination } from 'src/app/models/api/pagination.model';
import { SnackbarService } from './snackbar.service';
import { Router } from '@angular/router';
import { isNested } from 'src/app/helpers/utils.helper';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  constructor(
    private router: Router,
    private http: HttpClient,
    private snackBarService: SnackbarService
  ) {}

  async getForApi<T = null>(path: string, params: object | null = null): Promise<T> {
    return await this.handleResult(
      this.http.get<T>(this.getApiPath(path), {
        params: { ...params }
      })
    );
  }

  async getForApiWithPagination<T>(path: string, currentPage: number, parameters: object | null = null): Promise<Pagination<T>> {
    return await this.handleResultForPagination(
      this.http.get<Pagination<T>>(this.getApiPath(path), {
        observe: 'response',
        params: {
          ...parameters,
          page: currentPage,
          per_page: '10'
        }
      })
    );
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async postForApi<T>(path: string, body: any): Promise<T> {
    return await this.handleResult(this.http.post<T>(this.getApiPath(path), body));
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async patchForApi<T>(path: string, body: any): Promise<T> {
    return await this.handleResult(this.http.patch<T>(this.getApiPath(path), body));
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async deleteForApi(path: string, params: object = {}): Promise<any> {
    return await this.handleResult(
      this.http.delete(this.getApiPath(path), {
        params: { ...params }
      })
    );
  }

  fixAlgorithmStoreUrl(url: string): string {
    if (url.endsWith('/')) {
      return url.slice(0, -1);
    }
    return url;
  }

  async getForAlgorithmApi<T = null>(
    algo_store_url: string,
    path: string,
    parameters: object | null = null,
    showAuthError: boolean = true
  ): Promise<T> {
    algo_store_url = this.fixAlgorithmStoreUrl(algo_store_url);
    const request = this.http.get<T>(algo_store_url + path, {
      params: { ...parameters }
    });
    if (showAuthError) {
      return await this.handleResult(request);
    } else {
      return await this.handleResultWithoutAuthError(request);
    }
  }

  async getForAlgorithmApiWithPagination<T>(
    algo_store_url: string,
    path: string,
    currentPage: number,
    parameters: object | null = null
  ): Promise<Pagination<T>> {
    algo_store_url = this.fixAlgorithmStoreUrl(algo_store_url);
    return await this.handleResultForPagination(
      this.http.get<Pagination<T>>(algo_store_url + path, {
        observe: 'response',
        params: {
          ...parameters,
          page: currentPage,
          per_page: '10'
        }
      })
    );
  }

  async postForAlgorithmApi<T>(algo_store_url: string, path: string, body: object): Promise<T> {
    algo_store_url = this.fixAlgorithmStoreUrl(algo_store_url);
    return await this.handleResult(this.http.post<T>(algo_store_url + path, body));
  }

  async patchForAlgorithmApi<T>(algo_store_url: string, path: string, body: object): Promise<T> {
    algo_store_url = this.fixAlgorithmStoreUrl(algo_store_url);
    return await this.handleResult(this.http.patch<T>(algo_store_url + path, body));
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async deleteForAlgorithmApi(algo_store_url: string, path: string): Promise<any> {
    algo_store_url = this.fixAlgorithmStoreUrl(algo_store_url);
    return await this.handleResult(this.http.delete(algo_store_url + path));
  }

  private async handleResult<T = null>(request: Observable<T>): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      request.pipe(first()).subscribe(
        (response) => {
          resolve(response as T);
        },
        (error) => {
          const errorMsg = this.getErrorMsg(error);
          this.snackBarService.showMessage(errorMsg);
          reject(error);
        }
      );
    });
  }

  // Note: this could be reimplemented together with the handleResult function, but has
  // been explicitly separated to avoid having to complicate the handleResult function
  // with an additional parameter as that is used for almost all requests
  private async handleResultWithoutAuthError<T = null>(request: Observable<T>): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      request.pipe(first()).subscribe(
        (response) => {
          resolve(response as T);
        },
        (error) => {
          if (error.status !== HttpStatusCode.Unauthorized && error.status !== HttpStatusCode.Forbidden) {
            const errorMsg = this.getErrorMsg(error);
            this.snackBarService.showMessage(errorMsg);
          }
          reject(error);
        }
      );
    });
  }

  private async handleResultForPagination<T>(request: Observable<HttpResponse<Pagination<T>>>): Promise<Pagination<T>> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
          if (error instanceof HttpErrorResponse) {
            this.snackBarService.showMessage(error.message || 'An error occurred');
          } else {
            const errorMsg = this.getErrorMsg(error);
            this.snackBarService.showMessage(errorMsg);
          }

          reject(error);
        }
      );
    });
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private getErrorMsg(error: any): string {
    let errorMsg = error.error?.msg ? error.error?.msg : 'An error occurred';
    // Vantage6 server does request validation - if there are errors, they are returned in the response.
    // Here we append these errors to the error message.
    if (error.error?.errors) {
      errorMsg +=
        ': ' +
        Object.keys(error.error?.errors)
          .map((key) => {
            if (isNested(error.error?.errors[key])) {
              return key + ': ' + JSON.stringify(error.error?.errors[key]);
            } else {
              return key + ': ' + error.error?.errors[key];
            }
          })
          .join(', ');
    }
    return errorMsg;
  }

  private getApiPath(path: string): string {
    //TODO: Lazy loaded calls already include API path
    if (path.startsWith('/') && path.startsWith(environment.api_path)) {
      return environment.server_url + path;
    }
    return environment.server_url + environment.api_path + path;
  }
}
