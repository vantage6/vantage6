import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { Subject } from 'rxjs';
import { Location } from '@angular/common';
import { MatDialog } from '@angular/material/dialog';

import { ChangePassword } from 'src/app/models/api/auth.model';
import { PASSWORD_VALIDATORS } from 'src/app/models/constants/password_validators';
import { ApiService } from 'src/app/services/api.service';
import { createCompareValidator } from 'src/app/validators/compare.validator';
import { MessageDialog } from 'src/app/components/dialogs/message-dialog/message-dialog.component';
import { TranslateService } from '@ngx-translate/core';

@Component({
  selector: 'app-change-password',
  templateUrl: './change-password.component.html',
  styleUrls: ['./change-password.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class ChangePasswordComponent implements OnInit, OnDestroy {
  destroy$ = new Subject();
  form = this.fb.nonNullable.group(
    {
      oldPassword: ['', [Validators.required]],
      newPassword: ['', PASSWORD_VALIDATORS],
      newPasswordRepeat: ['', [Validators.required]]
    },
    { validators: [createCompareValidator('newPassword', 'newPasswordRepeat')] }
  );

  constructor(
    private fb: FormBuilder,
    private location: Location,
    private dialog: MatDialog,
    private translateService: TranslateService,
    private apiService: ApiService
  ) {}

  async ngOnInit(): Promise<void> {}

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }

  async handleSubmit() {
    if (this.form.valid) {
      const result = await this.apiService.patchForApi<ChangePassword>('/password/change', {
        current_password: this.form.controls.oldPassword.value,
        new_password: this.form.controls.newPassword.value
      });
      const dialogRef = this.dialog.open(MessageDialog, {
        data: {
          title: 'Password changed',
          content: 'Your password has been changed successfully.',
          confirmButtonText: this.translateService.instant('general.close'),
          confirmButtonType: 'primary'
        }
      });

      dialogRef.afterClosed().subscribe(() => {
        this.goToPreviousPage();
      });
      // TODO handle errors
    }
  }

  handleCancel() {
    this.goToPreviousPage();
  }

  goToPreviousPage() {
    this.location.back();
  }
}
