import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA } from '@angular/material/dialog';

export interface DialogData {
  title: string;
  content: string;
  cancelButtonText: string;
  confirmButtonText: string;
  confirmButtonType: 'primary' | 'warn' | 'accent';
}

@Component({
  selector: 'app-confirm-dialog',
  templateUrl: 'confirm-dialog.component.html',
  styleUrls: ['./confirm-dialog.component.scss']
})
export class ConfirmDialogComponent {
  constructor(@Inject(MAT_DIALOG_DATA) public data: DialogData) {}
}
