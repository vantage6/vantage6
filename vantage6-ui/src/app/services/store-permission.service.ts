import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { OperationType, StoreResourceType, StoreRule } from 'src/app/models/api/rule.model';
import { StoreRuleService } from './store-rule.service';
import { AlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { PermissionService } from './permission.service';
import { environment } from 'src/environments/environment';

@Injectable({
  providedIn: 'root'
})
export class StorePermissionService {
  activeRules: StoreRule[] | null = null;
  store?: AlgorithmStore;

  initialized$ = new BehaviorSubject<boolean>(false);

  constructor(
    private storeRuleService: StoreRuleService,
    private permissionService: PermissionService
  ) {}

  isInitialized(): Observable<boolean> {
    return this.initialized$.asObservable();
  }

  async initialize(store: AlgorithmStore): Promise<void> {
    this.store = store;
    this.activeRules = await this.getStoreRules();
    this.initialized$.next(true);
  }

  clear(): void {
    this.activeRules = null;
  }

  // TODO implement separate function to check if allowed to view algorithms
  isAllowed(resource: StoreResourceType, operation: OperationType): boolean {
    return !!this.activeRules?.some((rule) => rule.name.toLowerCase() === resource && rule.operation.toLowerCase() === operation);
  }

  private async getStoreRules(): Promise<StoreRule[]> {
    if (!this.store) return [];
    const username = this.permissionService.activeUser?.username;
    const serverUrl = `${environment.server_url}${environment.api_path}`;
    return await this.storeRuleService.getRules(this.store.url, { no_pagination: 1, username: username, server_url: serverUrl });
  }
}
