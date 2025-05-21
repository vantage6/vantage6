import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { OperationType, StoreResourceType, StoreRule } from 'src/app/models/api/rule.model';
import { StoreRuleService } from './store-rule.service';
import { AlgorithmStore, AlgorithmViewPolicies, AvailableStorePolicies, StorePolicies } from 'src/app/models/api/algorithmStore.model';
import { environment } from 'src/environments/environment';
import { AlgorithmStoreService } from './algorithm-store.service';
import { POLICY_ALLOW_ALL_SERVERS } from '../models/constants/policies';

@Injectable({
  providedIn: 'root'
})
export class StorePermissionService {
  activeRules: StoreRule[] | null = null;
  publicPolicies: StorePolicies | null = null;
  store?: AlgorithmStore;
  canViewAlgorithms = false;
  isUserRegistered = false;

  initialized$ = new BehaviorSubject<boolean>(false);

  constructor(
    private storeRuleService: StoreRuleService,
    private algorithmStoreService: AlgorithmStoreService
  ) {}

  isInitialized(): Observable<boolean> {
    return this.initialized$.asObservable();
  }

  async initialize(store: AlgorithmStore): Promise<void> {
    this.store = store;
    this.publicPolicies = await this.algorithmStoreService.getAlgorithmStorePolicies(this.store.url, true);
    this.activeRules = await this.getStoreRules();
    this.canViewAlgorithms = await this.determineViewAlgorithms();
    this.initialized$.next(true);
  }

  clear(): void {
    this.activeRules = null;
  }

  isAllowed(resource: StoreResourceType, operation: OperationType): boolean {
    if (!this.isUserRegistered) return false;
    return !!this.activeRules?.some((rule) => rule.name.toLowerCase() === resource && rule.operation.toLowerCase() === operation);
  }

  private async getStoreRules(): Promise<StoreRule[]> {
    if (!this.store || !this.isServerAllowedToBeWhitelisted) {
      this.isUserRegistered = false;
      return [];
    }

    // get the rules
    try {
      const result = await this.storeRuleService.getRules(this.store.url, { no_pagination: 1, current_user: true }, false);
      this.isUserRegistered = true;
      return result;
    } catch (error) {
      this.isUserRegistered = false;
      return [];
    }
  }

  private isServerAllowedToBeWhitelisted(): boolean {
    // Determine if the server is potentialy whitelisted at the store. This is the
    // case if A) all stores are allowed to be whitelisted or B) the store is in the
    // list of explicitly allowed servers
    if (!this.publicPolicies) return false;
    const allowedServersPolicy = this.publicPolicies[AvailableStorePolicies.ALLOWED_SERVERS];
    return (
      allowedServersPolicy === POLICY_ALLOW_ALL_SERVERS ||
      (Array.isArray(allowedServersPolicy) && allowedServersPolicy.includes(`${environment.server_url}${environment.api_path}`))
    );
  }

  private async determineViewAlgorithms(): Promise<boolean> {
    // if anyone is allowed to view the algorithms, return true
    if (this.publicPolicies && this.publicPolicies[AvailableStorePolicies.ALGORITHM_VIEW] === AlgorithmViewPolicies.PUBLIC) {
      return true;
    }
    // otherwise check if the user is allowed to view the algorithms
    return (this.activeRules && this.isAllowed(StoreResourceType.ALGORITHM, OperationType.VIEW)) || false;
  }
}
