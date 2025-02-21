import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { routePaths } from 'src/app/routes';
import { Resource } from 'src/app/models/api/resource.model';
import { TranslateService } from '@ngx-translate/core';
import { CallbackFunction } from 'src/app/models/general.model';
import { HandleConfirmDialogService } from 'src/app/services/handle-confirm-dialog.service';
import { Subject } from 'rxjs';

@Component({
    selector: 'app-base-read',
    templateUrl: './base-read.component.html',
    styleUrl: './base-read.component.scss',
    standalone: false
})
export abstract class BaseReadComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  @Input() id = '';
  destroy$ = new Subject<void>();

  routes = routePaths;

  isLoading: boolean = true;
  canDelete: boolean = false;
  canEdit: boolean = false;

  constructor(
    protected handleConfirmDialogService: HandleConfirmDialogService,
    protected translateService: TranslateService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.initData();
  }

  ngOnDestroy() {
    this.destroy$.next();
  }

  protected abstract initData(): Promise<void>;

  protected async handleDeleteBase(
    resourceToDelete: Resource | null,
    deleteTitle: string,
    deleteContent: string,
    onSuccessfullDeleteFunc: CallbackFunction
  ): Promise<void> {
    if (!resourceToDelete) return;

    this.handleConfirmDialogService.handleConfirmDialog(
      deleteTitle,
      deleteContent,
      this.translateService.instant('general.delete'),
      'warn',
      onSuccessfullDeleteFunc
    );
  }
}
