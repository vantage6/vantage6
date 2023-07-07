import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { environment } from 'src/environments/environment';

@Injectable({
  providedIn: 'root'
})
export class VersionApiService {
  version: string;

  constructor(private http: HttpClient) { }

  async getVersion() : Promise<string> {
    if (this.version)
      return this.version;
    let response: any = await this.http.get(
      `${environment.api_url}/version`).toPromise();
    this.version = response.version;
    return this.version;
  }
}
