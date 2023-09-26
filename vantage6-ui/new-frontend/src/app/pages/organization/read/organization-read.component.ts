import { Component, Input, OnInit } from '@angular/core';
import { NodeStatus } from 'src/app/models/api/node.model';
import { Organization, OrganizationLazyProperties } from 'src/app/models/api/organization.model';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
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

  @Input() id = '';

  isLoading = true;
  organization?: Organization;
  collaborationTable?: TableData;

  constructor(private organizationService: OrganizationService) {}

  async ngOnInit(): Promise<void> {
    this.initData();
  }

  handleCollaborationClick(id: string): void {
    //TODO: Add navigation to collaboration page
    console.log(id);
  }

  handleNodeClick(id: number): void {
    //TODO: Add navigation to node page
    console.log(id);
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
