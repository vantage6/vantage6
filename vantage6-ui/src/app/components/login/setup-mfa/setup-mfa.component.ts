import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';

import { AuthService } from 'src/app/auth/services/auth.service';
import { ModalService } from 'src/app/services/common/modal.service';

@Component({
  selector: 'app-setup-mfa',
  templateUrl: './setup-mfa.component.html',
  styleUrls: ['./setup-mfa.component.scss'],
})
export class SetupMfaComponent implements OnInit {
  qr_url: string;
  otp_code: string;

  constructor(
    private authService: AuthService,
    private router: Router,
    private modalService: ModalService
  ) {}

  ngOnInit(): void {
    if (this.authService.qr_uri === undefined) {
      this.router.navigateByUrl('/login');
    } else {
      this.qr_url = this.authService.qr_uri;
      this.otp_code = this.authService.otp_code as string;
    }
  }

  showOtpCode() {
    this.modalService.openMessageModal([
      'If you are having difficulties scanning the QR code, please enter the following code manually in your authentication app.',
      this.otp_code,
    ]);
  }
}
