import { Injectable } from '@angular/core';
import { BehaviorSubject, Subject, takeUntil } from 'rxjs';
import { AlgorithmStore, AlgorithmStoreLazyProperties } from '../models/api/algorithmStore.model';
import { AlgorithmStoreService } from './algorithm-store.service';
import { PermissionService } from './permission.service';
import { CHOSEN_ALGORITHM_STORE } from '../models/constants/sessionStorage';

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
    private permissionService: PermissionService
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
    const collaboration = await this.getStore(id);
    this.store$.next(collaboration);
  }

  private async initData() {
    const storeIDFromSession = sessionStorage.getItem(CHOSEN_ALGORITHM_STORE);
    if (storeIDFromSession) {
      this.id = storeIDFromSession;
      const collaboration = await this.getStore(this.id);
      this.store$.next(collaboration);
    }
    this.isInitialized$.next(true);
  }

  private async getStore(id: string): Promise<AlgorithmStore> {
    return await this.algorithmStoreService.getAlgorithmStore(id, [AlgorithmStoreLazyProperties.Collaborations]);
  }
}
