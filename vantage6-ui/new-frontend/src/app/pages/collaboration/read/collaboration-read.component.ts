import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { Subject, Subscription, takeUntil } from 'rxjs';
import { ConfirmDialogComponent } from 'src/app/components/dialogs/confirm/confirm-dialog.component';
import { Collaboration, CollaborationLazyProperties } from 'src/app/models/api/collaboration.model';
import { NodeStatus } from 'src/app/models/api/node.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { NodeOnlineStatusMsg } from 'src/app/models/socket-messages.model';
import { routePaths } from 'src/app/routes';
import { CollaborationService } from 'src/app/services/collaboration.service';
import { PermissionService } from 'src/app/services/permission.service';
import { SocketioConnectService } from 'src/app/services/socketio-connect.service';

@Component({
  selector: 'app-collaboration-read',
  templateUrl: './collaboration-read.component.html'
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

  private nodeStatusUpdateSubscription?: Subscription;

  constructor(
    private dialog: MatDialog,
    private router: Router,
    private collaborationService: CollaborationService,
    private translateService: TranslateService,
    private permissionService: PermissionService,
    private socketioConnectService: SocketioConnectService
  ) {}

  async ngOnInit(): Promise<void> {
    this.canDelete = this.permissionService.isAllowed(ScopeType.ANY, ResourceType.COLLABORATION, OperationType.DELETE);
    this.canEdit = this.permissionService.isAllowed(ScopeType.ANY, ResourceType.COLLABORATION, OperationType.EDIT);
    await this.initData();
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

  private async initData(): Promise<void> {
    this.collaboration = await this.collaborationService.getCollaboration(this.id, [
      CollaborationLazyProperties.Organizations,
      CollaborationLazyProperties.Nodes
    ]);
    this.isLoading = false;
  }

  private onNodeStatusUpdate(nodeStatusUpdate: NodeOnlineStatusMsg): void {
    if (!this.collaboration) return;
    const node = this.collaboration.nodes.find((n) => n.id === nodeStatusUpdate.id);
    if (node) {
      node.status = nodeStatusUpdate.online ? NodeStatus.Online : NodeStatus.Offline;
    }
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
}
