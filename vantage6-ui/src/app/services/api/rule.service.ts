import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { environment } from 'src/environments/environment';

@Injectable({
  providedIn: 'root',
})
export class RuleService {
  constructor(private http: HttpClient) {}

  list() {
    return this.http.get<any>(environment.api_url + '/rule');
  }

  get(id: number) {}
}
