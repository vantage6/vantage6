import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogTitle, MatDialogContent, MatDialogActions, MatDialogClose } from '@angular/material/dialog';
import { CdkScrollable } from '@angular/cdk/scrolling';
import { MatButton } from '@angular/material/button';
import { TranslateModule } from '@ngx-translate/core';
import { ConfirmDialogOption } from 'src/app/models/application/confirmDialog.model';
import { NgIf } from '@angular/common';

export interface BaseDialogData {
  title: string;
  content: string;
  confirmButtonText: string;
  confirmButtonType: 'primary' | 'warn' | 'accent';
  secondOptionButtonText?: string;
  secondOptionButtonType?: 'primary' | 'warn' | 'accent';
}

export interface DialogData extends BaseDialogData {
  cancelButtonText: string;
}

@Component({
  selector: 'app-confirm-dialog',
  templateUrl: 'confirm-dialog.component.html',
  styleUrls: ['./confirm-dialog.component.scss'],
  imports: [MatDialogTitle, CdkScrollable, MatDialogContent, MatDialogActions, MatButton, MatDialogClose, TranslateModule, NgIf]
})
export class ConfirmDialogComponent {
  confirmDialogOption = ConfirmDialogOption;
  constructor(@Inject(MAT_DIALOG_DATA) public data: DialogData) {}
}
