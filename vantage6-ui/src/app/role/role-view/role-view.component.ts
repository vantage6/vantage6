import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';

import { Role, EMPTY_ROLE } from 'src/app/interfaces/role';

import { RoleService } from 'src/app/services/api/role.service';
import { UserPermissionService } from 'src/app/services/user-permission.service';

@Component({
  selector: 'app-role-view',
  templateUrl: './role-view.component.html',
  styleUrls: ['./role-view.component.scss'],
})
export class RoleViewComponent implements OnInit {
  @Input() role: Role = EMPTY_ROLE;
  @Output() deletingRole = new EventEmitter<Role>();
  @Output() editingRole = new EventEmitter<Role>();

  constructor(
    public userPermission: UserPermissionService,
    public roleService: RoleService
  ) {}

  ngOnInit(): void {}

  deleteRole(): void {
    console.log('delete role');
    // this.roleService.delete(this.role).subscribe(
    //   (data) => {
    //     this.deletingRole.emit(this.role);
    //   },
    //   (error) => {
    //     alert(error.error.msg);
    //   }
    // );
  }

  editRole(): void {
    // this.role.is_being_edited = true;
    // this.editingRole.emit(this.role);
    console.log('editing');
  }
}
