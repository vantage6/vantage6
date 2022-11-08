import { Injectable } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router } from '@angular/router';

@Injectable({
  providedIn: 'root',
})
export class SnackbarService {
  constructor(private snackBar: MatSnackBar, private router: Router) {}

  // Snackbar that opens with success background
  openNodeStatusSnackBar(msg: string, data: any, online: boolean) {
    let panelClass = online ? ['green-snackbar'] : ['red-snackbar'];
    const sb = this.snackBar.open(msg, 'View node', {
      verticalPosition: 'top',
      duration: 10000,
      panelClass: panelClass,
    });

    // define what happens if users click the button
    sb.onAction().subscribe(() => {
      this.router.navigate([`/node/${data.id}/view/${data.org_id}`]);
    });
  }

  // //Snackbar that opens with failure background
  // openFailureSnackBar() {
  //   this.snackBar.open('Invalid Login Credentials', 'Try again!', {
  //     duration: 6000,
  //     panelClass: ['red-snackbar'],
  //   });
  // }
}
