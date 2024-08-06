import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { FormControl, Validators } from '@angular/forms';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { Subject, Subscription, takeUntil } from 'rxjs';
import { ConfirmDialogComponent } from 'src/app/components/dialogs/confirm/confirm-dialog.component';
import { AlgorithmStore, EditAlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { Collaboration, CollaborationLazyProperties } from 'src/app/models/api/collaboration.model';
import { Study } from 'src/app/models/api/study.model';
import { BaseNode, NodeStatus } from 'src/app/models/api/node.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { TableData } from 'src/app/models/application/table.model';
import { NodeOnlineStatusMsg } from 'src/app/models/socket-messages.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmStoreService } from 'src/app/services/algorithm-store.service';
import { CollaborationService } from 'src/app/services/collaboration.service';
import { PermissionService } from 'src/app/services/permission.service';
import { SocketioConnectService } from 'src/app/services/socketio-connect.service';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { NodeService } from 'src/app/services/node.service';
import { printDate } from 'src/app/helpers/general.helper';

@Component({
  selector: 'app-collaboration-read',
  templateUrl: './collaboration-read.component.html',
  styleUrls: ['./collaboration-read.component.scss']
})
export class CollaborationReadComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  destroy$ = new Subject();
  nodeStatus = NodeStatus;
  routes = routePaths;

  @Input() id = '';

  isLoading = true;
  collaboration?: Collaboration;
  canDelete = false;
  canEdit = false;
  canCreateStudy = false;
  canCreateNodes = false;
  canCreateNodesOwnOrg = false;

  isEditAlgorithmStore = false;
  selectedAlgoStore?: AlgorithmStore;
  algoStoreNewName = new FormControl<string>('', [Validators.required]);

  isEditStudy = false;
  selectedStudy?: Study;
  studyTable?: TableData;

  private nodeStatusUpdateSubscription?: Subscription;

  constructor(
    private dialog: MatDialog,
    private router: Router,
    private collaborationService: CollaborationService,
    private algorithmStoreService: AlgorithmStoreService,
    private translateService: TranslateService,
    private permissionService: PermissionService,
    private socketioConnectService: SocketioConnectService,
    private chosenCollaborationService: ChosenCollaborationService,
    private nodeService: NodeService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.initData();
    this.setPermissions();
    this.nodeStatusUpdateSubscription = this.socketioConnectService
      .getNodeStatusUpdates()
      .subscribe((nodeStatusUpdate: NodeOnlineStatusMsg | null) => {
        if (nodeStatusUpdate) this.onNodeStatusUpdate(nodeStatusUpdate);
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
    this.nodeStatusUpdateSubscription?.unsubscribe();
  }

  public isMissingNodes(): boolean {
    return this.collaboration !== undefined && this.collaboration.nodes.length < this.collaboration.organizations.length;
  }

  public isMissingOwnOrgNode(): boolean {
    return (
      this.collaboration !== undefined &&
      this.collaboration.nodes.filter((node) => node.organization.id === this.permissionService.activeUser?.organization.id).length === 0
    );
  }

  private async initData(): Promise<void> {
    this.collaboration = await this.collaborationService.getCollaboration(this.id, [
      CollaborationLazyProperties.Organizations,
      CollaborationLazyProperties.Nodes,
      CollaborationLazyProperties.AlgorithmStores,
      CollaborationLazyProperties.Studies
    ]);
    this.studyTable = {
      columns: [
        {
          id: 'name',
          label: this.translateService.instant('collaboration.name')
        }
      ],
      rows: this.collaboration.studies.map((study) => ({
        id: study.id.toString(),
        columnData: {
          name: study.name
        }
      }))
    };
    this.isLoading = false;
  }

  private onNodeStatusUpdate(nodeStatusUpdate: NodeOnlineStatusMsg): void {
    if (!this.collaboration) return;
    const node = this.collaboration.nodes.find((n) => n.id === nodeStatusUpdate.id);
    if (node) {
      node.status = nodeStatusUpdate.online ? NodeStatus.Online : NodeStatus.Offline;
    }
  }

  private setPermissions() {
    this.permissionService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((initialized) => {
        if (initialized) {
          this.canDelete = this.permissionService.isAllowed(ScopeType.ANY, ResourceType.COLLABORATION, OperationType.DELETE);
          this.canEdit = this.permissionService.isAllowed(ScopeType.ANY, ResourceType.COLLABORATION, OperationType.EDIT);
          this.canCreateStudy = this.permissionService.isAllowedForCollab(
            ResourceType.STUDY,
            OperationType.CREATE,
            this.collaboration || null
          );
          this.canCreateNodes = this.permissionService.isAllowedForCollab(
            ResourceType.NODE,
            OperationType.CREATE,
            this.collaboration || null
          );
          const activeUserOrgId = this.permissionService.activeUser?.organization.id;
          this.canCreateNodesOwnOrg =
            this.permissionService.isAllowedForOrg(ResourceType.NODE, OperationType.CREATE, activeUserOrgId || null) &&
            (this.collaboration?.organizations || []).some((org) => org.id === activeUserOrgId);
        }
      });
  }

  async onRegisterMissingNodes(allOrgs: boolean = true): Promise<void> {
    if (!this.collaboration) return;
    // find organizations that are not yet registered
    let missingOrganizations = this.collaboration?.organizations.filter(
      (organization) => !this.collaboration?.nodes.some((node) => node.organization.id === organization.id)
    );
    if (!allOrgs) {
      missingOrganizations = missingOrganizations.filter(
        (organization) => organization.id === this.permissionService.activeUser?.organization.id
      );
    }
    await this.nodeService.registerNodes(this.collaboration, missingOrganizations);
    // refresh the collaboration
    this.initData();
  }

  selectAlgoStore(id: number): void {
    this.selectedAlgoStore = this.collaboration?.algorithm_stores.find((algoStore) => algoStore.id === id);
  }

  handleStudyClick(id: string): void {
    this.router.navigate([routePaths.study, id]);
  }

  async handleDelete(): Promise<void> {
    if (!this.collaboration) return;

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: this.translateService.instant('collaboration-read.delete-dialog.title', { name: this.collaboration.name }),
        content: this.translateService.instant('collaboration-read.delete-dialog.content'),
        confirmButtonText: this.translateService.instant('general.delete'),
        confirmButtonType: 'warn'
      }
    });

    dialogRef
      .afterClosed()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (result) => {
        if (result === true) {
          if (!this.collaboration) return;
          this.isLoading = true;
          await this.collaborationService.deleteCollaboration(this.collaboration.id.toString());
          this.router.navigate([routePaths.collaborations]);
        }
      });
  }

  handleAlgoStoreEditStart(): void {
    this.isEditAlgorithmStore = true;
  }

  async handleAlgoStoreEditSubmit(): Promise<void> {
    if (!this.collaboration || !this.selectedAlgoStore || !this.algoStoreNewName.value) return;
    this.isEditAlgorithmStore = false;

    const algoStoreEdit: EditAlgorithmStore = {
      name: this.algoStoreNewName.value
    };
    const result = await this.algorithmStoreService.edit(this.selectedAlgoStore.id.toString(), algoStoreEdit);
    if (result.id) {
      this.selectedAlgoStore.name = result.name;
      const storeToUpdate = this.collaboration.algorithm_stores.find((store) => store.id === result.id);
      if (storeToUpdate) {
        storeToUpdate.name = result.name;
      }
    }
    // refresh the chosen collaboration
    this.chosenCollaborationService.refresh(this.collaboration.id.toString());
  }

  handleAlgoStoreEditCancel(): void {
    this.isEditAlgorithmStore = false;
  }

  handleAlgoStoreDelete(): void {
    if (!this.collaboration || !this.selectedAlgoStore) return;

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: this.translateService.instant('collaboration.algorithm-store.delete-dialog.title', {
          name: this.selectedAlgoStore.name,
          collaboration: this.collaboration.name
        }),
        content: this.translateService.instant('collaboration.algorithm-store.delete-dialog.content'),
        confirmButtonText: this.translateService.instant('general.delete'),
        confirmButtonType: 'warn'
      }
    });

    dialogRef
      .afterClosed()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (result) => {
        if (result === true) {
          if (!this.collaboration || !this.selectedAlgoStore) return;
          await this.algorithmStoreService.delete(this.selectedAlgoStore.id.toString());

          // update list of stores
          this.collaboration.algorithm_stores = this.collaboration.algorithm_stores.filter(
            (store) => store.id !== this.selectedAlgoStore?.id
          );
          this.selectedAlgoStore = undefined;

          // refresh the chosen collaboration. Don't specify the collaboration id to
          // force refresh, as the store may be part of other collaborations as well
          this.chosenCollaborationService.refresh();
        }
      });
  }

  getNodeLabelText(node: BaseNode): string {
    return node.status === NodeStatus.Online ? node.name : node.name + this.nodeOfflineText(node);
  }

  private nodeOfflineText(node: BaseNode): string {
    if (!node.last_seen) {
      return ` (${this.translateService.instant('general.offline')} - never been online)`;
    } else {
      return ` (${this.translateService.instant('general.offline')} since ${printDate(node.last_seen)})`;
    }
  }
}
