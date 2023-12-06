import { Component, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { MessageDialogComponent } from 'src/app/components/dialogs/message-dialog/message-dialog.component';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';

@Component({
  selector: 'app-setup-mfa',
  templateUrl: './setup-mfa.component.html',
  styleUrls: ['./setup-mfa.component.scss']
})
export class SetupMfaComponent implements OnInit {
  routes = routePaths;

  constructor(
    private router: Router,
    private dialog: MatDialog,
    private authService: AuthService,
    private translateService: TranslateService
  ) {}

  ngOnInit(): void {
    if (!this.authService.qr_uri) {
      this.router.navigate([routePaths.login]);
    }
  }

  getQRUrl(): string {
    return this.authService.qr_uri;
  }

  showOtpCode() {
    this.dialog.open(MessageDialogComponent, {
      data: {
        title: this.translateService.instant('mfa.setup.manual.title'),
        content: [this.translateService.instant('mfa.setup.manual.message'), this.authService.otp_code],
        confirmButtonText: this.translateService.instant('general.close'),
        confirmButtonType: 'primary'
      }
    });
  }
}
