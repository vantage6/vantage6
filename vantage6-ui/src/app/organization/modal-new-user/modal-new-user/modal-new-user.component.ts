import { Component, Input, OnInit } from '@angular/core';
// import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';

@Component({
  selector: 'app-modal-new-user',
  templateUrl: './modal-new-user.component.html',
  styleUrls: ['./modal-new-user.component.scss'],
})
export class ModalNewUserComponent implements OnInit {
  @Input() message: string = '';

  username: string = '';
  password: string = '';
  password_repeated: string = '';
  email: string = '';
  first_name: string = '';
  last_name: string = '';
  roles: Role[] = [];
  rules: Rule[] = [];

  constructor() {} // public activeModal: NgbActiveModal

  ngOnInit(): void {}

  // closeModal(): void {
  //   this.activeModal.close();
  // }
}
