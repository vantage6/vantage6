import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { EMPTY_NODE } from 'src/app/interfaces/node';
import { EMPTY_ROLE, Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { UtilsService } from 'src/app/services/common/utils.service';
import { RoleDataService } from 'src/app/services/data/role-data.service';
import { RuleDataService } from 'src/app/services/data/rule-data.service';
import { ResType } from 'src/app/shared/enum';

@Component({
  selector: 'app-role-view-single',
  templateUrl: './role-view-single.component.html',
  styleUrls: ['./role-view-single.component.scss'],
})
export class RoleViewSingleComponent implements OnInit {
  route_id: number | null = null;
  role: Role = EMPTY_ROLE;
  rules: Rule[] = [];

  constructor(
    private activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    private roleDataService: RoleDataService,
    private ruleDataService: RuleDataService,
    private utilsService: UtilsService
  ) {}

  ngOnInit(): void {
    this.userPermission.isInitialized().subscribe((ready: boolean) => {
      if (ready) {
        this.init();
      }
    });
  }

  async init() {
    (await this.ruleDataService.list()).subscribe((rules) => {
      this.rules = rules;
    });

    this.activatedRoute.paramMap.subscribe((params) => {
      this.route_id = this.utilsService.getId(params, ResType.NODE);
      if (this.route_id === EMPTY_NODE.id) {
        return; // cannot get organization
      }
      this.setup();
    });
  }

  async setup() {
    this.setRole();
  }

  async setRole(): Promise<void> {
    this.role = await this.roleDataService.get(
      this.route_id as number,
      this.rules
    );
  }

  goBackToPreviousPage() {
    this.utilsService.goToPreviousPage();
  }
}
