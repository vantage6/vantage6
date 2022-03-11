import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { Resource } from 'src/app/shared/types';

@Injectable({
  providedIn: 'root',
})
export abstract class StoreBaseService {
  constructor() {}

  abstract setSingle(resource: Resource): void;

  abstract setList(resources: Resource[]): void;

  abstract getSingle(): Observable<Resource>;

  abstract getList(): Observable<Resource[]>;

  abstract add(resource: Resource): void;

  abstract remove(resource: Resource): void;

  abstract hasListStored(): boolean;
}
