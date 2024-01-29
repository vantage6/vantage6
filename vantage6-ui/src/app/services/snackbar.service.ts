import { Injectable } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateService } from '@ngx-translate/core';

@Injectable({
  providedIn: 'root'
})
export class SnackbarService {
  constructor(
    private snackBar: MatSnackBar,
    private translateService: TranslateService
  ) {}

  showMessage(message: string) {
    this.snackBar.open(message, this.translateService.instant('general.close'), {
      duration: 20000 //Auto close after 20 seconds
    });
  }

  dismiss() {
    this.snackBar.dismiss();
  }
}
