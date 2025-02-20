import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogTitle, MatDialogContent, MatDialogActions, MatDialogClose } from '@angular/material/dialog';
import { CdkScrollable } from '@angular/cdk/scrolling';
import { NgFor } from '@angular/common';
import { MatButton } from '@angular/material/button';
import { TranslateModule } from '@ngx-translate/core';

export interface DialogData {
  title: string;
  content: string[];
  confirmButtonText: string;
  confirmButtonType: 'primary' | 'warn' | 'accent';
}

@Component({
  selector: 'app-message-dialog',
  templateUrl: './message-dialog.component.html',
  standalone: true,
  imports: [MatDialogTitle, CdkScrollable, MatDialogContent, NgFor, MatDialogActions, MatButton, MatDialogClose, TranslateModule]
})
export class MessageDialogComponent {
  constructor(@Inject(MAT_DIALOG_DATA) public data: DialogData) {}
}
