import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA } from '@angular/material/dialog';

export interface DialogData {
  log: string;
}

@Component({
  selector: 'log-dialog',
  templateUrl: 'log-dialog.component.html',
  styleUrls: ['./log-dialog.component.scss']
})
export class LogDialog {
  constructor(@Inject(MAT_DIALOG_DATA) public data: DialogData) {}
}
