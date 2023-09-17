import { Component, OnInit } from '@angular/core';
import { MatSelectChange } from '@angular/material/select';
import { NodeStatus } from 'src/app/models/api/node.model';
import { BaseOrganization, Organization, OrganizationLazyProperties } from 'src/app/models/api/organization.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { TableData } from 'src/app/models/application/table.model';
import { AuthService } from 'src/app/services/auth.service';
import { OrganizationService } from 'src/app/services/organization.service';

@Component({
  selector: 'app-organization-read',
  templateUrl: './organization-read.component.html',
  styleUrls: ['./organization-read.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class OrganizationReadComponent implements OnInit {
  nodeStatus = NodeStatus;

  isLoading = false;
  organizations: BaseOrganization[] = [];
  selectedOrganization?: Organization;
  collaborationTable?: TableData;
  canAdministerMultiple: boolean = false;
  canCreate: boolean = false;

  constructor(
    private organizationService: OrganizationService,
    private authService: AuthService
  ) {}

  async ngOnInit(): Promise<void> {
    this.canAdministerMultiple = this.authService.hasResourceInScope(ScopeType.GLOBAL, ResourceType.ORGANIZATION);
    this.canCreate = this.authService.isOperationAllowed(ScopeType.ORGANIZATION, ResourceType.ORGANIZATION, OperationType.CREATE);

    if (this.canAdministerMultiple) {
      this.organizations = await this.organizationService.getOrganizations();
    } else {
      const user = await this.authService.getUser();
      this.handleOrganizationChange(user.organization.id.toString());
    }
  }

  async handleOrganizationSelect(e: MatSelectChange): Promise<void> {
    this.handleOrganizationChange(e.value);
  }

  async handleOrganizationChange(id: string): Promise<void> {
    this.isLoading = true;
    this.selectedOrganization = await this.organizationService.getOrganization(id, [
      OrganizationLazyProperties.Collaborations,
      OrganizationLazyProperties.Nodes
    ]);
    this.collaborationTable = {
      columns: [{ id: 'name', label: 'Name' }],
      rows: this.selectedOrganization.collaborations.map((_) => ({ id: _.id.toString(), columnData: { name: _.name } }))
    };
    this.isLoading = false;
  }

  handleCollaborationClick(id: string): void {
    //TODO: Add navigation to collaboration page
    console.log(id);
  }

  handleNodeClick(id: number): void {
    //TODO: Add navigation to node page
    console.log(id);
  }
}
