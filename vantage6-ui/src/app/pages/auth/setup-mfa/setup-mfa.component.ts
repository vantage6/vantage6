import { Component, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Router, RouterLink } from '@angular/router';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { MessageDialogComponent } from 'src/app/components/dialogs/message-dialog/message-dialog.component';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { LoginErrorService } from 'src/app/services/login-error.service';
import { MatCard, MatCardHeader, MatCardTitle, MatCardContent } from '@angular/material/card';
import { QRCodeComponent } from 'angularx-qrcode';
import { MatButton } from '@angular/material/button';
import { NgIf } from '@angular/common';
import { AlertComponent } from '../../../components/alerts/alert/alert.component';

@Component({
  selector: 'app-setup-mfa',
  templateUrl: './setup-mfa.component.html',
  styleUrls: ['./setup-mfa.component.scss'],
  imports: [
    MatCard,
    MatCardHeader,
    MatCardTitle,
    MatCardContent,
    QRCodeComponent,
    MatButton,
    RouterLink,
    NgIf,
    AlertComponent,
    TranslateModule
  ]
})
export class SetupMfaComponent implements OnInit {
  routes = routePaths;

  constructor(
    public loginErrorService: LoginErrorService,
    private router: Router,
    private dialog: MatDialog,
    private authService: AuthService,
    private translateService: TranslateService
  ) {}

  ngOnInit(): void {
    this.loginErrorService.clearError();
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
