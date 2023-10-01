import { Component, OnInit } from '@angular/core';
import { BaseNode, Node, NodeLazyProperties, NodeStatus } from '../../../models/api/node.model';
import { NodeService } from 'src/app/services/node.service';
import { BaseOrganization } from 'src/app/models/api/organization.model';
import { OrganizationService } from 'src/app/services/organization.service';
import { MatSelectChange } from '@angular/material/select';
import { CollaborationService } from 'src/app/services/collaboration.service';
import { BaseCollaboration } from 'src/app/models/api/collaboration.model';

@Component({
  selector: 'app-node-read',
  templateUrl: './node-read.component.html',
  styleUrls: ['./node-read.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class NodeReadComponent implements OnInit {
  nodeStatus = NodeStatus;

  isLoading = true;
  nodes: BaseNode[] = [];
  organizations: BaseOrganization[] = [];
  collaborations: BaseCollaboration[] = [];
  selectedNode?: Node;

  constructor(
    private nodeService: NodeService,
    private organizationService: OrganizationService,
    private collaborationService: CollaborationService
  ) {}

  ngOnInit(): void {
    this.initData();
  }

  async handleFilterChange(e: MatSelectChange): Promise<void> {
    const values = e.value.split(';');
    if (values[0] === 'organization') {
      this.nodeService.getNodesForOrganization(e.value[1]);
    } else if (values[0] === 'collaboration') {
      this.nodeService.getNodesForCollaboration(e.value[1]);
    }
  }

  async handleNodeChange(nodeID: number): Promise<void> {
    await this.getNode(nodeID);
  }

  private async initData(): Promise<void> {
    this.isLoading = true;

    this.organizations = await this.organizationService.getOrganizations();
    this.collaborations = await this.collaborationService.getCollaborations();
    this.nodes = await this.nodeService.getNodes();
    this.isLoading = false;
  }

  private async getNode(nodeID: number): Promise<void> {
    this.selectedNode = undefined;
    this.selectedNode = await this.nodeService.getNode(nodeID.toString(), [
      NodeLazyProperties.Organization,
      NodeLazyProperties.Collaboration
    ]);
  }
}
