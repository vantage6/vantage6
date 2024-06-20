import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { Subject, takeUntil } from 'rxjs';
import { routePaths } from 'src/app/routes';
import { ConfirmDialogComponent } from '../../dialogs/confirm/confirm-dialog.component';
import { MatDialog } from '@angular/material/dialog';
import { Resource } from 'src/app/models/api/resource.model';
import { TranslateService } from '@ngx-translate/core';
import { CallbackFunction } from 'src/app/models/general.model';

@Component({
  selector: 'app-base-read',
  templateUrl: './base-read.component.html',
  styleUrl: './base-read.component.scss'
})
export abstract class BaseReadComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  @Input() id = '';

  destroy$ = new Subject();
  routes = routePaths;

  isLoading: boolean = true;
  canDelete: boolean = false;
  canEdit: boolean = false;

  constructor(
    protected dialog: MatDialog,
    protected translateService: TranslateService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.initData();
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }

  protected abstract initData(): Promise<void>;

  protected async handleDeleteBase(
    resourceToDelete: Resource | null,
    deleteTitle: string,
    deleteContent: string,
    onSuccessfullDeleteFunc: CallbackFunction
  ): Promise<void> {
    if (!resourceToDelete) return;

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: deleteTitle,
        content: deleteContent,
        confirmButtonText: this.translateService.instant('general.delete'),
        confirmButtonType: 'warn'
      }
    });

    dialogRef
      .afterClosed()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (result) => {
        if (result === true) {
          onSuccessfullDeleteFunc();
        }
      });
  }
}
