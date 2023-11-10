import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { Role, RoleLazyProperties } from 'src/app/models/api/role.model';
import { RoleService } from 'src/app/services/role.service';

@Component({
  selector: 'app-role-read',
  templateUrl: './role-read.component.html',
  styleUrls: ['./role-read.component.scss']
})
export class RoleReadComponent implements OnInit {
  @HostBinding('class') class = 'card-container';

  @Input() id = '';

  constructor(private roleService: RoleService) {}

  isLoading = true;
  role?: Role;

  async ngOnInit(): Promise<void> {
    await this.initData();
  }

  private async initData(): Promise<void> {
    this.role = await this.roleService.getRole(this.id, [RoleLazyProperties.Rules, RoleLazyProperties.Users]);
    this.isLoading = false;
  }
}
