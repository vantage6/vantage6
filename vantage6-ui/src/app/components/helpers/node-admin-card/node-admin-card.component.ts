import { Component, EventEmitter, Input, OnDestroy, OnInit, Output } from '@angular/core';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { Subject, Subscription, takeUntil } from 'rxjs';
import { printDate } from 'src/app/helpers/general.helper';
import { Collaboration } from 'src/app/models/api/collaboration.model';
import { BaseNode, NodeStatus } from 'src/app/models/api/node.model';
import { BaseOrganization } from 'src/app/models/api/organization.model';
import { OperationType, ResourceType } from 'src/app/models/api/rule.model';
import { NodeOnlineStatusMsg } from 'src/app/models/socket-messages.model';
import { NodeService } from 'src/app/services/node.service';
import { PermissionService } from 'src/app/services/permission.service';
import { SocketioConnectService } from 'src/app/services/socketio-connect.service';
import { MatCard, MatCardHeader, MatCardTitle, MatCardContent } from '@angular/material/card';
import { NgIf, NgFor } from '@angular/common';
import { MatButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { AlertComponent } from '../../alerts/alert/alert.component';
import { ChipComponent } from '../chip/chip.component';

@Component({
    selector: 'app-node-admin-card',
    templateUrl: './node-admin-card.component.html',
    styleUrl: './node-admin-card.component.scss',
    imports: [
        MatCard,
        MatCardHeader,
        MatCardTitle,
        NgIf,
        MatButton,
        MatIcon,
        MatCardContent,
        AlertComponent,
        NgFor,
        ChipComponent,
        TranslateModule
    ]
})
export class NodeAdminCardComponent implements OnInit, OnDestroy {
  @Input() nodes?: BaseNode[];
  @Input() organizations?: BaseOrganization[];
  @Input() collaboration?: Collaboration;
  @Output() nodesUpdated: EventEmitter<void> = new EventEmitter<void>();
  destroy$ = new Subject();
  nodeStatus = NodeStatus;

  canCreateNodes = false;
  canCreateNodesOwnOrg = false;

  private nodeStatusUpdateSubscription?: Subscription;

  constructor(
    private translateService: TranslateService,
    private permissionService: PermissionService,
    private socketioConnectService: SocketioConnectService,
    private nodeService: NodeService
  ) {}

  async ngOnInit(): Promise<void> {
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
    return this.nodes != null && this.organizations != null && this.nodes.length < this.organizations.length;
  }

  public isMissingOwnOrgNode(): boolean {
    return (
      this.nodes != null &&
      this.nodes.filter((node) => node.organization.id === this.permissionService.activeUser?.organization.id).length === 0
    );
  }

  async onRegisterMissingNodes(allOrgs: boolean = true): Promise<void> {
    if (!this.collaboration || !this.organizations) return;
    // find organizations that are not yet registered
    let missingOrganizations = this.organizations.filter(
      (organization) => this.nodes && !this.nodes.some((node) => node.organization.id === organization.id)
    );
    if (!allOrgs) {
      missingOrganizations = missingOrganizations.filter(
        (organization) => organization.id === this.permissionService.activeUser?.organization.id
      );
    }
    await this.nodeService.registerNodes([this.collaboration], missingOrganizations, true);
    // refresh the collaboration
    this.nodesUpdated.emit();
  }

  private onNodeStatusUpdate(nodeStatusUpdate: NodeOnlineStatusMsg): void {
    if (!this.nodes) return;
    const node = this.nodes.find((n) => n.id === nodeStatusUpdate.id);
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
          if (!this.collaboration) return;
          this.canCreateNodes = this.permissionService.isAllowedForCollab(ResourceType.NODE, OperationType.CREATE, this.collaboration);
          const activeUserOrgId = this.permissionService.activeUser?.organization.id;
          this.canCreateNodesOwnOrg =
            this.permissionService.isAllowedForOrg(ResourceType.NODE, OperationType.CREATE, activeUserOrgId || null) &&
            (this.organizations || []).some((org) => org.id === activeUserOrgId);
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
