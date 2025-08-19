import { Component, HostBinding, OnDestroy, OnInit } from '@angular/core';
import { BaseNode, Node, NodeEdit, NodeLazyProperties, NodeSortProperties, NodeStatus } from 'src/app/models/api/node.model';
import { NodeService } from 'src/app/services/node.service';
import { OrganizationSortProperties } from 'src/app/models/api/organization.model';
import { OrganizationService } from 'src/app/services/organization.service';
import { CollaborationService } from 'src/app/services/collaboration.service';
import { CollaborationSortProperties } from 'src/app/models/api/collaboration.model';
import { FormControl, Validators, ReactiveFormsModule } from '@angular/forms';
import { OperationType, ResourceType } from 'src/app/models/api/rule.model';
import { Pagination, PaginationLinks } from 'src/app/models/api/pagination.model';
import { PageEvent, MatPaginator } from '@angular/material/paginator';
import { PermissionService } from 'src/app/services/permission.service';
import { SocketioConnectService } from 'src/app/services/socketio-connect.service';
import { NodeOnlineStatusMsg } from 'src/app/models/socket-messages.model';
import { Subject, Subscription, takeUntil } from 'rxjs';
import { MatDialog } from '@angular/material/dialog';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { MessageDialogComponent } from 'src/app/components/dialogs/message-dialog/message-dialog.component';
import { FileService } from 'src/app/services/file.service';
import { printDate } from 'src/app/helpers/general.helper';
import { ITreeInputNode, ITreeSelectedValue } from 'src/app/components/helpers/tree-dropdown/tree-dropdown.component';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { TreeDropdownComponent } from '../../../../components/helpers/tree-dropdown/tree-dropdown.component';
import { NgIf, NgFor } from '@angular/common';
import { MatCard, MatCardContent } from '@angular/material/card';
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle,
  MatExpansionPanelContent
} from '@angular/material/expansion';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { ChipComponent } from '../../../../components/helpers/chip/chip.component';
import { MatButton } from '@angular/material/button';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { TaskService } from 'src/app/services/task.service';
import { ConfirmDialogComponent } from 'src/app/components/dialogs/confirm/confirm-dialog.component';
import { ConfirmDialogOption } from 'src/app/models/application/confirmDialog.model';
import { SnackbarService } from 'src/app/services/snackbar.service';

@Component({
  selector: 'app-node-read',
  templateUrl: './node-read.component.html',
  styleUrls: ['./node-read.component.scss'],
  imports: [
    PageHeaderComponent,
    TreeDropdownComponent,
    NgIf,
    MatCard,
    MatCardContent,
    MatAccordion,
    NgFor,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatExpansionPanelContent,
    MatProgressSpinner,
    MatFormField,
    MatLabel,
    MatInput,
    ReactiveFormsModule,
    ChipComponent,
    MatButton,
    MatPaginator,
    TranslateModule
  ]
})
export class NodeReadComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  nodeStatus = NodeStatus;
  printDate = printDate;

  treeNodes: ITreeInputNode[] = [];
  selectedTreeNodes: ITreeSelectedValue[] = [];

  name = new FormControl<string>('', [Validators.required]);
  isLoading: boolean = true;
  isEdit: boolean = false;
  nodes: BaseNode[] = [];
  selectedNode?: Node;
  pagination: PaginationLinks | null = null;
  currentPage: number = 1;

  destroy$ = new Subject();

  private nodeStatusUpdateSubscription?: Subscription;

  constructor(
    private dialog: MatDialog,
    private nodeService: NodeService,
    private organizationService: OrganizationService,
    private collaborationService: CollaborationService,
    private permissionService: PermissionService,
    private socketioConnectService: SocketioConnectService,
    private translateService: TranslateService,
    private fileService: FileService,
    private chosenCollaborationService: ChosenCollaborationService,
    private taskService: TaskService,
    private matDialog: MatDialog,
    private snackBarService: SnackbarService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.initData();
    this.nodeStatusUpdateSubscription = this.socketioConnectService
      .getNodeStatusUpdates()
      .subscribe((nodeStatusUpdate: NodeOnlineStatusMsg | null) => {
        if (nodeStatusUpdate) this.onNodeStatusUpdate(nodeStatusUpdate);
      });
  }

  ngOnDestroy(): void {
    this.nodeStatusUpdateSubscription?.unsubscribe();
    this.destroy$.next(true);
    this.destroy$.complete();
  }

  async handleSelectedTreeNodesChange(newSelected: ITreeSelectedValue[]): Promise<void> {
    // Tree-dropdown component supports multiselect, but the API call for retrieving paginated nodes does not (yet) support multiple filter parameters. For now, the first value is selected.
    this.selectedTreeNodes = newSelected.length ? [newSelected[0]] : [];
    await this.getNodes(newSelected[0]);
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
      const nodeToUpdate = this.nodes.find((node) => node.id === result.id);
      if (nodeToUpdate) {
        nodeToUpdate.name = result.name;
      }
    }
  }

  handleEditCancel(): void {
    this.isEdit = false;
  }

  canEdit(orgId: number): boolean {
    return this.permissionService.isAllowedForOrg(ResourceType.NODE, OperationType.EDIT, orgId);
  }

  canKill(): boolean {
    // we currently only allow killing tasks from the UI for organization members
    // of the same node
    return (
      this.permissionService.isAllowedForCollab(
        ResourceType.EVENT,
        OperationType.SEND,
        this.chosenCollaborationService.collaboration$.value
      ) && this.permissionService.activeUser?.organization?.id === this.selectedNode?.organization?.id
    );
  }

  handleKillNodeTasks(): void {
    if (!this.selectedNode) return;

    const dialogRef = this.matDialog.open(ConfirmDialogComponent, {
      data: {
        title: this.translateService.instant('node-edit.kill-tasks-dialog.title', { name: this.selectedNode.name }),
        content: this.translateService.instant('node-edit.kill-tasks-dialog.content'),
        confirmButtonText: this.translateService.instant('general.delete'),
        confirmButtonType: 'warn'
      }
    });

    dialogRef
      .afterClosed()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (result) => {
        if (result === ConfirmDialogOption.PRIMARY) {
          this.killNodeTasks();
          this.snackBarService.showMessage(this.translateService.instant('node-edit.kill-tasks-dialog.success'));
        }
      });
  }

  killNodeTasks(): void {
    if (!this.selectedNode) return;
    this.taskService.killNodeTasks(this.selectedNode.id);
  }

  onNodeStatusUpdate(nodeStatusUpdate: NodeOnlineStatusMsg): void {
    for (const node of this.nodes) {
      if (node.id === nodeStatusUpdate.id) {
        node.status = nodeStatusUpdate.online ? NodeStatus.Online : NodeStatus.Offline;
        if (this.selectedNode && this.selectedNode.id === node.id) {
          this.selectedNode.status = node.status;
        }
        break;
      }
    }
  }

  async generateNewAPIKey(): Promise<void> {
    if (!this.selectedNode) return;
    const new_api_key = await this.nodeService.resetApiKey(this.selectedNode?.id.toString());
    this.downloadResettedApiKey(new_api_key.api_key, this.selectedNode.name);

    this.dialog.open(MessageDialogComponent, {
      data: {
        title: this.translateService.instant('api-key-download-dialog.title'),
        content: [this.translateService.instant('api-key-download-dialog.reset-message')],
        confirmButtonText: this.translateService.instant('general.close'),
        confirmButtonType: 'default'
      }
    });
  }

  private downloadResettedApiKey(api_key: string, node_name: string): void {
    const filename = `API_key_${node_name}.txt`;
    this.fileService.downloadTxtFile(api_key, filename);
  }

  private async initData(): Promise<void> {
    this.isLoading = true;

    const loadOrganizations = this.organizationService.getOrganizations({ sort: OrganizationSortProperties.Name });
    const loadCollaborations = this.collaborationService.getCollaborations({ sort: CollaborationSortProperties.Name });
    await Promise.all([loadOrganizations, loadCollaborations, this.getNodes()]).then((values) => {
      this.treeNodes = [
        {
          isFolder: true,
          children: values[0].map((organization) => {
            return {
              isFolder: false,
              children: [],
              label: organization.name,
              code: organization.id,
              parentCode: this.translateService.instant('node.organization').toLowerCase()
            };
          }),
          label: this.translateService.instant('node.organization'),
          code: this.translateService.instant('node.organization').toLowerCase()
        },
        {
          isFolder: true,
          children: values[1].map((collaboration) => {
            return {
              isFolder: false,
              children: [],
              label: collaboration.name,
              code: collaboration.id,
              parentCode: this.translateService.instant('node.collaboration').toLowerCase()
            };
          }),
          label: this.translateService.instant('node.collaboration'),
          code: this.translateService.instant('node.collaboration').toLowerCase()
        }
      ];
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

  private async getNodes(selectedValue?: ITreeSelectedValue): Promise<void> {
    let result: Pagination<BaseNode> | null = null;
    if (selectedValue && selectedValue.parentCode === 'organization') {
      result = await this.nodeService.getPaginatedNodes(this.currentPage, {
        organization_id: selectedValue.code.toString(),
        sort: NodeSortProperties.Name
      });
    } else if (selectedValue && selectedValue.parentCode === 'collaboration') {
      result = await this.nodeService.getPaginatedNodes(this.currentPage, {
        collaboration_id: selectedValue.code.toString(),
        sort: NodeSortProperties.Name
      });
    } else {
      result = await this.nodeService.getPaginatedNodes(this.currentPage, { sort: NodeSortProperties.Name });
    }
    this.nodes = result.data;
    this.pagination = result.links;
  }
}
