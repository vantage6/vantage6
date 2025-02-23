import { Component, HostBinding, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { BaseCollaboration, CollaborationSortProperties, GetCollaborationParameters } from 'src/app/models/api/collaboration.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { routePaths } from 'src/app/routes';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { CollaborationService } from 'src/app/services/collaboration.service';
import { EncryptionService } from 'src/app/services/encryption.service';
import { PermissionService } from 'src/app/services/permission.service';

@Component({
  selector: 'app-choose-collaboration',
  templateUrl: './choose-collaboration.component.html',
  styleUrls: ['./choose-collaboration.scss']
})
export class ChooseCollaborationComponent implements OnInit {
  @HostBinding('class') class = 'card-container';
  collaborations: BaseCollaboration[] = [];
  isLoading = true;
  routes = routePaths;

  constructor(
    private router: Router,
    private collaborationService: CollaborationService,
    private chosenCollaborationService: ChosenCollaborationService,
    private permissionService: PermissionService,
    public encryptionService: EncryptionService
  ) {}

  async ngOnInit() {
    await this.initData();
    this.isLoading = false;
  }

  async handleCollaborationClick(collaboration: BaseCollaboration) {
    this.isLoading = true;
    await this.chosenCollaborationService.setCollaboration(collaboration.id.toString());
    if (this.permissionService.isAllowedWithMinScope(ScopeType.COLLABORATION, ResourceType.SESSION, OperationType.VIEW)) {
      this.router.navigate([routePaths.sessions]);
    } else {
      this.router.navigate([routePaths.analyzeHome]);
    }
    this.isLoading = false;
  }

  private async initData(): Promise<void> {
    const params: GetCollaborationParameters = {
      sort: CollaborationSortProperties.Name
    };
    const activeOrgId = this.permissionService.getActiveOrganizationID();
    if (activeOrgId) {
      params.organization_id = activeOrgId.toString();
    }
    this.collaborations = await this.collaborationService.getCollaborations(params);
  }
}
