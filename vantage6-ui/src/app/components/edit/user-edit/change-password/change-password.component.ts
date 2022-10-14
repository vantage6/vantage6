import { Component, Input, OnInit } from '@angular/core';
import { getEmptyUser, User } from 'src/app/interfaces/user';
import { UserApiService } from 'src/app/services/api/user-api.service';
import { ModalService } from 'src/app/services/common/modal.service';

@Component({
  selector: 'app-change-password',
  templateUrl: './change-password.component.html',
  styleUrls: [
    '../../../../shared/scss/buttons.scss',
    './change-password.component.scss',
  ],
})
export class ChangePasswordComponent implements OnInit {
  @Input() user: User = getEmptyUser();
  old_password: string = '';
  new_password: string = '';
  new_password_repeated: string = '';

  constructor(
    private userApiService: UserApiService,
    private modalService: ModalService
  ) {}

  ngOnInit(): void {}

  hasFilledInPasswords(): boolean {
    return (
      this.old_password.length > 0 &&
      this.new_password.length > 0 &&
      this.new_password === this.new_password_repeated
    );
  }

  async savePassword(): Promise<void> {
    this.userApiService
      .change_password(this.old_password, this.new_password)
      .subscribe(
        (data: any) => {
          this.modalService.openMessageModal([
            'Your password was changed successfully!',
          ]);
          this.old_password = '';
          this.new_password = '';
          this.new_password_repeated = '';
        },
        (error: any) => {
          this.modalService.openErrorModal(error.error.msg);
        }
      );
  }
}
