import { Injectable, OnDestroy } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Subject, takeUntil } from 'rxjs';
import { CallbackFunction } from 'src/app/models/general.model';
import { ConfirmDialogComponent } from '../components/dialogs/confirm/confirm-dialog.component';

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
    confirmButtonType: string,
    onSuccessfullDeleteFunc: CallbackFunction
  ): Promise<void> {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: title,
        content: content,
        confirmButtonText: confirmButtonText,
        confirmButtonType: confirmButtonType
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
