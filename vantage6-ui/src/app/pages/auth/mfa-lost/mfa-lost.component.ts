import { Component, OnInit } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { LoginErrorService } from 'src/app/services/login-error.service';
import { MatCard, MatCardHeader, MatCardTitle, MatCardContent } from '@angular/material/card';
import { MatButton } from '@angular/material/button';
import { NgIf } from '@angular/common';
import { AlertWithButtonComponent } from '../../../components/alerts/alert-with-button/alert-with-button.component';
import { AlertComponent } from '../../../components/alerts/alert/alert.component';
import { TranslateModule } from '@ngx-translate/core';

@Component({
    selector: 'app-mfa-lost',
    templateUrl: './mfa-lost.component.html',
    styleUrls: ['./mfa-lost.component.scss'],
    imports: [
        MatCard,
        MatCardHeader,
        MatCardTitle,
        MatCardContent,
        MatButton,
        NgIf,
        AlertWithButtonComponent,
        RouterLink,
        AlertComponent,
        TranslateModule
    ]
})
export class MfaLostComponent implements OnInit {
  executed_request = false;
  responseMsg = '';
  routes = routePaths;

  constructor(
    public loginErrorService: LoginErrorService,
    private router: Router,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.loginErrorService.clearError();
    if (!this.authService.username || !this.authService.password) {
      this.router.navigate([routePaths.login]);
    }
  }

  async onSubmit(): Promise<void> {
    const responseMsg = await this.authService.MFALost();
    if (responseMsg) {
      this.executed_request = true;
      this.responseMsg = responseMsg;
    }
  }
}
