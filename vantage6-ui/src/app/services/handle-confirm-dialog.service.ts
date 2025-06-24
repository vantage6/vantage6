import { Injectable, OnDestroy } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Subject, takeUntil } from 'rxjs';
import { CallbackFunction } from 'src/app/models/general.model';
import { ConfirmDialogComponent, BaseDialogData } from '../components/dialogs/confirm/confirm-dialog.component';
import { ConfirmDialogOption } from '../models/application/confirmDialog.model';

@Injectable({
  providedIn: 'root'
})
export class HandleConfirmDialogService implements OnDestroy {
  destroy$ = new Subject();

  constructor(private dialog: MatDialog) {}

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }

  async handleConfirmDialog(
    title: string,
    content: string,
    confirmButtonText: string,
    confirmButtonType: 'primary' | 'warn' | 'accent',
    onSuccessfullDeleteFunc: CallbackFunction,
    secondOptionButtonText?: string,
    secondOptionButtonType?: 'primary' | 'warn' | 'accent'
  ): Promise<void> {
    const dialogData: BaseDialogData = {
      title: title,
      content: content,
      confirmButtonText: confirmButtonText,
      confirmButtonType: confirmButtonType
    };
    if (secondOptionButtonText) {
      dialogData.secondOptionButtonText = secondOptionButtonText;
      dialogData.secondOptionButtonType = secondOptionButtonType;
    }

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: dialogData
    });

    dialogRef
      .afterClosed()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (result) => {
        if (result === ConfirmDialogOption.PRIMARY) {
          onSuccessfullDeleteFunc();
        }
      });
  }
}
