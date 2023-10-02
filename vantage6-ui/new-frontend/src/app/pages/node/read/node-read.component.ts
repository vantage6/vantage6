import { Component, OnInit } from '@angular/core';
import { BaseNode, Node, NodeEdit, NodeLazyProperties, NodeSortProperties, NodeStatus } from '../../../models/api/node.model';
import { NodeService } from 'src/app/services/node.service';
import { BaseOrganization, OrganizationSortProperties } from 'src/app/models/api/organization.model';
import { OrganizationService } from 'src/app/services/organization.service';
import { MatSelectChange } from '@angular/material/select';
import { CollaborationService } from 'src/app/services/collaboration.service';
import { BaseCollaboration, CollaborationSortProperties } from 'src/app/models/api/collaboration.model';
import { MatDialog } from '@angular/material/dialog';
import { FormControl, Validators } from '@angular/forms';
import { AuthService } from 'src/app/services/auth.service';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';

@Component({
  selector: 'app-node-read',
  templateUrl: './node-read.component.html',
  styleUrls: ['./node-read.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class NodeReadComponent implements OnInit {
  nodeStatus = NodeStatus;

  name = new FormControl<string>('', [Validators.required]);
  isLoading: boolean = true;
  canEdit: boolean = false;
  isEdit: boolean = false;
  nodes: BaseNode[] = [];
  organizations: BaseOrganization[] = [];
  collaborations: BaseCollaboration[] = [];
  selectedNode?: Node;

  constructor(
    private nodeService: NodeService,
    private organizationService: OrganizationService,
    private collaborationService: CollaborationService,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.canEdit = this.authService.isOperationAllowed(ScopeType.ANY, ResourceType.NODE, OperationType.EDIT);
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
    this.isEdit = false;
    await this.getNode(nodeID);
  }

  handleEditStart(): void {
    this.isEdit = true;
  }

  async handleEditSubmit(): Promise<void> {
    if (!this.selectedNode || !this.name.value) return;

    this.isEdit = false;
    const nodeEdit: NodeEdit = {
      name: this.name.value
    };
    const result = await this.nodeService.editNode(this.selectedNode.id.toString(), nodeEdit);
    if (result.id) {
      this.selectedNode.name = result.name;
      this.nodes.find((node) => node.id === result.id)!.name = result.name;
    }
  }

  handleEditCancel(): void {
    this.isEdit = false;
  }

  private async initData(): Promise<void> {
    this.isLoading = true;

    this.organizations = await this.organizationService.getOrganizations(OrganizationSortProperties.Name);
    this.collaborations = await this.collaborationService.getCollaborations(CollaborationSortProperties.Name);
    this.nodes = await this.nodeService.getNodes(NodeSortProperties.Name);
    this.isLoading = false;
  }

  private async getNode(nodeID: number): Promise<void> {
    this.selectedNode = undefined;
    this.selectedNode = await this.nodeService.getNode(nodeID.toString(), [
      NodeLazyProperties.Organization,
      NodeLazyProperties.Collaboration
    ]);
    this.name.setValue(this.selectedNode.name);
  }
}
