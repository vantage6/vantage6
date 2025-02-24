import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Router, RouterLink } from '@angular/router';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { Subject, Subscription, takeUntil } from 'rxjs';
import { ConfirmDialogComponent } from 'src/app/components/dialogs/confirm/confirm-dialog.component';
import { downloadFile } from 'src/app/helpers/file.helper';
import { BaseCollaboration } from 'src/app/models/api/collaboration.model';
import { NodeStatus } from 'src/app/models/api/node.model';
import { Organization, OrganizationLazyProperties } from 'src/app/models/api/organization.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { TableData } from 'src/app/models/application/table.model';
import { NodeOnlineStatusMsg } from 'src/app/models/socket-messages.model';
import { routePaths } from 'src/app/routes';
import { NodeService } from 'src/app/services/node.service';
import { OrganizationService } from 'src/app/services/organization.service';
import { PermissionService } from 'src/app/services/permission.service';
import { SocketioConnectService } from 'src/app/services/socketio-connect.service';
import { NgIf, NgFor } from '@angular/common';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { MatIconButton, MatButton } from '@angular/material/button';
import { MatMenuTrigger, MatMenu, MatMenuItem } from '@angular/material/menu';
import { MatIcon } from '@angular/material/icon';
import { MatCard, MatCardHeader, MatCardTitle, MatCardContent } from '@angular/material/card';
import { TableComponent } from '../../../../components/table/table.component';
import { AlertComponent } from '../../../../components/alerts/alert/alert.component';
import { ChipComponent } from '../../../../components/helpers/chip/chip.component';
import { MatProgressSpinner } from '@angular/material/progress-spinner';

@Component({
    selector: 'app-organization-read',
    templateUrl: './organization-read.component.html',
    styleUrls: ['./organization-read.component.scss'],
    imports: [
        NgIf,
        PageHeaderComponent,
        MatIconButton,
        MatMenuTrigger,
        MatIcon,
        MatMenu,
        MatMenuItem,
        RouterLink,
        MatCard,
        MatCardHeader,
        MatCardTitle,
        MatCardContent,
        MatButton,
        TableComponent,
        AlertComponent,
        NgFor,
        ChipComponent,
        MatProgressSpinner,
        TranslateModule
    ]
})
export class OrganizationReadComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  routes = routePaths;
  nodeStatus = NodeStatus;
  destroy$ = new Subject();

  @Input() id: string = '';

  isLoading: boolean = true;
  canEdit: boolean = false;
  canDelete: boolean = false;
  canCreateNodes = false;
  organization?: Organization;
  collaborationTable?: TableData;

  private nodeStatusUpdateSubscription?: Subscription;

  constructor(
    private router: Router,
    private dialog: MatDialog,
    private translateService: TranslateService,
    private organizationService: OrganizationService,
    private nodeService: NodeService,
    private permissionService: PermissionService,
    private socketioConnectService: SocketioConnectService
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
    this.destroy$.next(true);
    this.nodeStatusUpdateSubscription?.unsubscribe();
  }

  handleDownload(): void {
    downloadFile(this.organization?.public_key || '', `public_key_organization_${this.organization?.name}.txt`);
  }

  handleCollaborationClick(id: string): void {
    this.router.navigate([routePaths.collaboration, id]);
  }

  public isMissingNodes(): boolean {
    return this.organization != null && this.organization.nodes.length < this.organization.collaborations.length;
  }

  getCollaborationsWithMissingNodes(): BaseCollaboration[] {
    if (!this.organization) return [];
    return this.organization?.collaborations.filter(
      (collaboration) => !this.organization?.nodes.some((node) => node.collaboration.id === collaboration.id)
    );
  }

  getCollaborationsWithMissingNodeNames(): string {
    const collabsWithMissingNodes = this.getCollaborationsWithMissingNodes().map((collaboration) => collaboration.name);
    return collabsWithMissingNodes.join(', ');
  }

  async onRegisterMissingNodes(): Promise<void> {
    if (!this.organization) return;

    const missingCollabs = this.getCollaborationsWithMissingNodes();
    this.nodeService.registerNodes(missingCollabs, [this.organization], false);
  }

  async handleDelete(): Promise<void> {
    if (!this.organization) return;

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: this.translateService.instant('organization-read.delete-dialog.title', { name: this.organization.name }),
        content: this.translateService.instant('organization-read.delete-dialog.content'),
        confirmButtonText: this.translateService.instant('general.delete'),
        confirmButtonType: 'warn'
      }
    });

    dialogRef
      .afterClosed()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (result) => {
        if (result === true) {
          if (!this.organization) return;
          this.isLoading = true;
          await this.organizationService.deleteOrganization(this.organization.id.toString());
          this.router.navigate([routePaths.organizations]);
        }
      });
  }

  private async initData() {
    this.organization = await this.organizationService.getOrganization(this.id, [
      OrganizationLazyProperties.Collaborations,
      OrganizationLazyProperties.Nodes
    ]);
    this.collaborationTable = {
      columns: [{ id: 'name', label: this.translateService.instant('collaboration.name') }],
      rows: this.organization.collaborations.map((_) => ({ id: _.id.toString(), columnData: { name: _.name } }))
    };
    this.setPermissions();
    this.isLoading = false;
  }

  private onNodeStatusUpdate(nodeStatusUpdate: NodeOnlineStatusMsg): void {
    if (!this.organization) return;
    const node = this.organization.nodes.find((n) => n.id === nodeStatusUpdate.id);
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
          this.canEdit =
            !!this.organization &&
            this.permissionService.isAllowedForOrg(ResourceType.ORGANIZATION, OperationType.EDIT, this.organization.id);
          this.canDelete = this.permissionService.isAllowed(ScopeType.GLOBAL, ResourceType.ORGANIZATION, OperationType.DELETE);
          this.canCreateNodes =
            !!this.organization && this.permissionService.isAllowedForOrg(ResourceType.NODE, OperationType.CREATE, this.organization.id);
        }
      });
  }
}
