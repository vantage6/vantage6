import { Component, HostBinding, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { MatDialog } from '@angular/material/dialog';

import { PASSWORD_VALIDATORS } from 'src/app/validators/passwordValidators';
import { createCompareValidator } from 'src/app/validators/compare.validator';
import { MessageDialogComponent } from 'src/app/components/dialogs/message-dialog/message-dialog.component';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { Router } from '@angular/router';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { createUnEqualValidator } from 'src/app/validators/unequal.validator';
import { LoginErrorService } from 'src/app/services/login-error.service';
import { TokenStorageService } from 'src/app/services/token-storage.service';
import { PageHeaderComponent } from '../../../components/page-header/page-header.component';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatFormField, MatLabel, MatError } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { NgIf } from '@angular/common';
import { MatButton } from '@angular/material/button';
import { AlertComponent } from '../../../components/alerts/alert/alert.component';

@Component({
    selector: 'app-change-password',
    templateUrl: './change-password.component.html',
    imports: [
        PageHeaderComponent,
        MatCard,
        MatCardContent,
        ReactiveFormsModule,
        MatFormField,
        MatLabel,
        MatInput,
        NgIf,
        MatError,
        MatButton,
        AlertComponent,
        TranslateModule
    ]
})
export class ChangePasswordComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';

  destroy$ = new Subject();
  form = this.fb.nonNullable.group(
    {
      oldPassword: ['', [Validators.required]],
      newPassword: ['', [Validators.required, ...PASSWORD_VALIDATORS]],
      newPasswordRepeat: ['', [Validators.required]]
    },
    { validators: [createCompareValidator('newPassword', 'newPasswordRepeat'), createUnEqualValidator('oldPassword', 'newPassword')] }
  );
  username: string = '';

  constructor(
    public loginErrorService: LoginErrorService,
    private fb: FormBuilder,
    private router: Router,
    private dialog: MatDialog,
    private translateService: TranslateService,
    private authService: AuthService,
    private tokenStorageService: TokenStorageService
  ) {}

  ngOnInit(): void {
    this.loginErrorService.clearError();
    this.username = this.tokenStorageService.getUsername() || '';
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }

  async handleSubmit(): Promise<void> {
    if (this.form.valid) {
      await this.authService.changePassword(this.form.controls.oldPassword.value, this.form.controls.newPassword.value);

      const dialogRef = this.dialog.open(MessageDialogComponent, {
        data: {
          title: this.translateService.instant('change-password.success-dialog.title'),
          content: [this.translateService.instant('change-password.success-dialog.message')],
          confirmButtonText: this.translateService.instant('general.close'),
          confirmButtonType: 'primary'
        }
      });

      dialogRef
        .afterClosed()
        .pipe(takeUntil(this.destroy$))
        .subscribe(() => {
          this.goToPreviousPage();
        });
    }
  }

  handleCancel(): void {
    this.goToPreviousPage();
  }

  private goToPreviousPage(): void {
    this.router.navigate([routePaths.home]);
  }
}
