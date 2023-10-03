import { Component, OnInit } from '@angular/core';
import { BaseNode, Node, NodeEdit, NodeLazyProperties, NodeSortProperties, NodeStatus } from '../../../models/api/node.model';
import { NodeService } from 'src/app/services/node.service';
import { BaseOrganization, OrganizationSortProperties } from 'src/app/models/api/organization.model';
import { OrganizationService } from 'src/app/services/organization.service';
import { MatSelectChange } from '@angular/material/select';
import { CollaborationService } from 'src/app/services/collaboration.service';
import { BaseCollaboration, CollaborationSortProperties } from 'src/app/models/api/collaboration.model';
import { FormControl, Validators } from '@angular/forms';
import { AuthService } from 'src/app/services/auth.service';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { Pagination, PaginationLinks } from 'src/app/models/api/pagination.model';
import { PageEvent } from '@angular/material/paginator';

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
  pagination: PaginationLinks | null = null;
  currentPage: number = 1;
  filterType: string = '';
  filterValue: string = '';

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
    if (e.value) {
      const values = e.value.split(';');
      this.filterType = values[0];
      this.filterValue = values[1];
    } else {
      this.filterType = '';
      this.filterValue = '';
    }
    await this.getNodes();
  }

  async handlePageEvent(e: PageEvent) {
    this.currentPage = e.pageIndex + 1;
    await this.getNodes();
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

    const loadOrganizations = this.organizationService.getOrganizations(OrganizationSortProperties.Name);
    const loadCollaborations = await this.collaborationService.getCollaborations(CollaborationSortProperties.Name);
    await Promise.all([loadOrganizations, loadCollaborations, this.getNodes()]).then((values) => {
      this.organizations = values[0];
      this.collaborations = values[1];
    });

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

  private async getNodes(): Promise<void> {
    let result: Pagination<BaseNode> | null = null;
    if (this.filterType === 'organization') {
      result = await this.nodeService.getPaginatedNodes(this.currentPage, {
        organization_id: this.filterValue,
        sort: NodeSortProperties.Name
      });
    } else if (this.filterType === 'collaboration') {
      result = await this.nodeService.getPaginatedNodes(this.currentPage, {
        collaboration_id: this.filterValue,
        sort: NodeSortProperties.Name
      });
    } else {
      result = await this.nodeService.getPaginatedNodes(this.currentPage, { sort: NodeSortProperties.Name });
    }

    this.nodes = result.data;
    this.pagination = result.links;
  }
}
