import { Component, OnInit } from '@angular/core';
import { Location } from '@angular/common';

import { EMPTY_ROLE, Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';

import { RoleService } from 'src/app/services/api/role.service';
import { UserPermissionService } from 'src/app/services/user-permission.service';
import { RoleEditService } from '../role-edit.service';

@Component({
  selector: 'app-role-edit',
  templateUrl: './role-edit.component.html',
  styleUrls: ['./role-edit.component.scss'],
})
export class RoleEditComponent implements OnInit {
  role: Role = EMPTY_ROLE;

  constructor(
    private location: Location,
    public userPermission: UserPermissionService,
    private roleService: RoleService,
    private roleEditService: RoleEditService
  ) {}

  ngOnInit(): void {
    this.roleEditService.getRole().subscribe((role) => {
      this.role = role;
    });
  }

  saveEdit(): void {
    let request;
    if (this.role.is_being_created) {
      request = this.roleService.create(this.role);
    } else {
      request = this.roleService.update(this.role);
    }

    request.subscribe(
      (data) => {
        this.goBack();
      },
      (error) => {
        alert(error.error.msg);
      }
    );
  }

  cancelEdit(): void {
    this.goBack();
  }

  updateAddedRules($event: Rule[]) {
    this.role.rules = $event;
  }

  goBack(): void {
    // go back to previous page
    this.location.back();
  }
}
