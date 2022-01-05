import { Component, OnInit } from '@angular/core';
import { mergeMap } from 'rxjs/operators';
import { Router } from '@angular/router';
import { forkJoin } from 'rxjs';

import { User } from '../interfaces/user';
import { Role } from '../interfaces/role';
import { Rule } from '../interfaces/rule';

import { UserPermissionService } from '../services/user-permission.service';
import { UserService } from '../services/api/user.service';
import { OrganizationService } from '../services/api/organization.service';
import { ModalService } from '../services/modal.service';
import { RoleService } from '../services/api/role.service';

@Component({
  selector: 'app-organization',
  templateUrl: './organization.component.html',
  styleUrls: ['./organization.component.scss'],
})
export class OrganizationComponent implements OnInit {
  organization_details: any = null;
  organization_users: User[] = [];
  roles: Role[] = [];
  all_rules: Rule[] = [];
  userId: number = 0;

  constructor(
    private userPermission: UserPermissionService,
    private userService: UserService,
    private organizationService: OrganizationService,
    private roleService: RoleService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.userPermission.getUserId().subscribe((id) => {
      this.userId = id;
      this.getOrganizationDetails();
    });
    this.userPermission.getRuleDescriptions().subscribe((rules) => {
      this.all_rules = rules;
    });
  }

  getOrganizationDetails(): void {
    if (this.userId === 0) return;
    // first obtain user information to get organization id, then obtain
    // organization information
    this.userService
      .get(this.userId)
      .pipe(
        mergeMap((user_data) =>
          this.organizationService.get(user_data.organization.id)
        )
      )
      .subscribe(
        (data) => {
          this.organization_details = data;
          this.collectUsers();
        },
        (err) => {
          console.log(err);
        }
      );
  }

  collectUsers(): void {
    this.organization_users = [];

    // collect users for current organization
    let req_users = this.userService.list(this.organization_details.id);

    // collect roles for current organization
    let req_roles = this.roleService.list(this.organization_details.id, true);

    // join users, roles and rules requests to set organization page variables
    forkJoin([req_users, req_roles]).subscribe(
      (data: any) => {
        let users = data[0];
        this.roles = [];
        for (let role of data[1]) {
          let rule_ids: Rule[] = [];
          for (let rule of role.rules) {
            rule_ids.push({ id: rule.id });
          }
          this.roles.push({
            id: role.id,
            name: role.name,
            description: role.description,
            organization_id: role.organization ? role.organization.id : null,
            rules: rule_ids,
          });
        }
        for (let user of users) {
          let user_roles: Role[] = [];
          if (user.roles) {
            user.roles.forEach((role: any) => {
              let r = this._getDescription(role.id, this.roles);
              user_roles.push(r);
            });
          }
          let user_rules: Rule[] = [];
          if (user.rules) {
            user.rules.forEach((rule: any) => {
              let r = this._getDescription(rule.id, this.all_rules);
              user_rules.push(r);
            });
          }
          this.organization_users.push({
            id: user.id,
            first_name: user.firstname,
            last_name: user.lastname,
            email: user.email,
            roles: user_roles,
            rules: user_rules,
          });
        }
      },
      (error) => {
        console.log(error);
      }
    );
  }

  createUser(): void {
    this.router.navigate(['user/create']);
  }

  private _getDescription(id: number, descriptions: any[]) {
    for (let d of descriptions) {
      if (d.id === id) {
        return d;
      }
    }
  }
}
