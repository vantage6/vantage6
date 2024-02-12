import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { Subject, Subscription, takeUntil } from 'rxjs';
import { downloadFile } from 'src/app/helpers/file.helper';
import { NodeStatus } from 'src/app/models/api/node.model';
import { Organization, OrganizationLazyProperties } from 'src/app/models/api/organization.model';
import { OperationType, ResourceType } from 'src/app/models/api/rule.model';
import { TableData } from 'src/app/models/application/table.model';
import { NodeOnlineStatusMsg } from 'src/app/models/socket-messages.model';
import { routePaths } from 'src/app/routes';
import { OrganizationService } from 'src/app/services/organization.service';
import { PermissionService } from 'src/app/services/permission.service';
import { SocketioConnectService } from 'src/app/services/socketio-connect.service';

@Component({
  selector: 'app-organization-read',
  templateUrl: './organization-read.component.html',
  styleUrls: ['./organization-read.component.scss']
})
export class OrganizationReadComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  routes = routePaths;
  nodeStatus = NodeStatus;
  destroy$ = new Subject();

  @Input() id: string = '';

  isLoading: boolean = true;
  canEdit: boolean = false;
  organization?: Organization;
  collaborationTable?: TableData;

  private nodeStatusUpdateSubscription?: Subscription;

  constructor(
    private router: Router,
    private translateService: TranslateService,
    private organizationService: OrganizationService,
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
        }
      });
  }
}
