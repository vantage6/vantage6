import { Component, Input, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { downloadFile } from 'src/app/helpers/file.helper';
import { NodeStatus } from 'src/app/models/api/node.model';
import { Organization, OrganizationLazyProperties } from 'src/app/models/api/organization.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { OrganizationService } from 'src/app/services/organization.service';

@Component({
  selector: 'app-organization-read',
  templateUrl: './organization-read.component.html',
  styleUrls: ['./organization-read.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class OrganizationReadComponent implements OnInit {
  routes = routePaths;
  nodeStatus = NodeStatus;

  @Input() id: string = '';

  isLoading: boolean = true;
  canEdit: boolean = false;
  organization?: Organization;
  collaborationTable?: TableData;

  constructor(
    private router: Router,
    private organizationService: OrganizationService,
    private authService: AuthService
  ) {}

  async ngOnInit(): Promise<void> {
    this.canEdit =
      this.authService.isOperationAllowed(ScopeType.GLOBAL, ResourceType.ORGANIZATION, OperationType.EDIT) ||
      this.authService.isOperationAllowed(ScopeType.ORGANIZATION, ResourceType.ORGANIZATION, OperationType.EDIT) ||
      this.authService.isOperationAllowed(ScopeType.COLLABORATION, ResourceType.ORGANIZATION, OperationType.EDIT);
    await this.initData();
  }

  handleDownload(): void {
    downloadFile(this.organization?.public_key || '', `public_key_organization_${this.organization?.name}.txt`);
  }

  handleCollaborationClick(id: string): void {
    this.router.navigate([routePaths.collaboration, id]);
  }

  private async initData() {
    this.organization = await this.organizationService.getOrganization(this.id, [
      OrganizationLazyProperties.Collaborations,
      OrganizationLazyProperties.Nodes
    ]);
    this.collaborationTable = {
      columns: [{ id: 'name', label: 'Name' }],
      rows: this.organization.collaborations.map((_) => ({ id: _.id.toString(), columnData: { name: _.name } }))
    };
    this.isLoading = false;
  }
}
