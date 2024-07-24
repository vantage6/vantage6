import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, Subject, takeUntil } from 'rxjs';
import { AlgorithmStore, AlgorithmStoreLazyProperties } from 'src/app/models/api/algorithmStore.model';
import { AlgorithmStoreService } from './algorithm-store.service';
import { PermissionService } from './permission.service';
import { CHOSEN_ALGORITHM_STORE } from 'src/app/models/constants/sessionStorage';
import { StorePermissionService } from './store-permission.service';

@Injectable({
  providedIn: 'root'
})
export class ChosenStoreService {
  id: string = '';
  isInitialized$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);
  store$: BehaviorSubject<AlgorithmStore | null> = new BehaviorSubject<AlgorithmStore | null>(null);
  destroy$ = new Subject();

  constructor(
    private algorithmStoreService: AlgorithmStoreService,
    private permissionService: PermissionService,
    private storePermissionService: StorePermissionService
  ) {
    this.permissionService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((initialized) => {
        if (initialized) {
          this.initData();
        }
      });
  }

  async setStore(id: string) {
    this.id = id;
    sessionStorage.setItem(CHOSEN_ALGORITHM_STORE, id);
    this.setup();
  }

  isInitialized(): Observable<boolean> {
    return this.isInitialized$.asObservable();
  }

  getCurrentStore(): Observable<AlgorithmStore | null> {
    return this.store$.asObservable();
  }

  private async initData() {
    const storeIDFromSession = sessionStorage.getItem(CHOSEN_ALGORITHM_STORE);
    if (storeIDFromSession) {
      this.id = storeIDFromSession;
      await this.setup();
    }
    this.isInitialized$.next(true);
  }

  private async setup() {
    const store = await this.getStore(this.id);
    this.store$.next(store);
    // initialize store permission service
    this.storePermissionService.initialize(store);
  }

  private async getStore(id: string): Promise<AlgorithmStore> {
    return await this.algorithmStoreService.getAlgorithmStore(id, [AlgorithmStoreLazyProperties.Collaborations]);
  }
}
