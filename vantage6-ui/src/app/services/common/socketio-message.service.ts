import { Injectable } from '@angular/core';

import { dictEmpty } from 'src/app/shared/utils';
import { Collaboration } from 'src/app/interfaces/collaboration';
import { Organization } from 'src/app/interfaces/organization';
import { CollabDataService } from '../data/collab-data.service';
import { OrgDataService } from '../data/org-data.service';
import { SnackbarService } from './snackbar.service';
import { SocketioConnectService } from './socketio-connect.service';
import { Sentiment, TaskStatus } from 'src/app/shared/enum';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';

@Injectable({
  providedIn: 'root',
})
export class SocketioMessageService {
  organizations: Organization[] = [];
  collaborations: Collaboration[] = [];

  constructor(
    private socketioConnectService: SocketioConnectService,
    private orgDataService: OrgDataService,
    private collabDataService: CollabDataService,
    private snackbarService: SnackbarService,
    private userPermission: UserPermissionService
  ) {
    this.userPermission.isInitialized().subscribe((ready) => {
      if (ready) {
        this.setupResources();
      }
    });

    this.subscribeToSocket();
  }

  subscribeToSocket(): void {
    this.socketioConnectService.getNodeStatusUpdates().subscribe((update) => {
      this.createNodeMessage(update);
    });
    this.socketioConnectService
      .getAlgorithmStatusUpdates()
      .subscribe((update) => {
        this.onAlgorithmStatusChange(update);
      });
    this.socketioConnectService.getTaskCreatedUpdates().subscribe((update) => {
      this.onCreatedTask(update);
    });
  }

  async setupResources() {
    (await this.orgDataService.list()).subscribe((orgs) => {
      this.organizations = orgs;
    });
    (await this.collabDataService.list()).subscribe((collabs) => {
      this.collaborations = collabs;
    });
  }

  createNodeMessage(update_dict: any) {
    if (dictEmpty(update_dict)) {
      return; // ignore initialization values;
    } else if (update_dict['online']) {
      this.onNodeOnline(update_dict);
    } else {
      this.onNodeOffline(update_dict);
    }
  }

  private onNodeOnline(data: any) {
    this.snackbarService.openNodeStatusSnackBar(
      `The node '${data.name}' just came online!`,
      data,
      true
    );
  }

  private onNodeOffline(data: any) {
    this.snackbarService.openNodeStatusSnackBar(
      `The node '${data.name}' just went offline!`,
      data,
      false
    );
  }

  isPositiveStatus(status: string): boolean {
    return (
      status === TaskStatus.ACTIVE ||
      status === TaskStatus.PENDING ||
      status === TaskStatus.INITIALIZING ||
      status === TaskStatus.COMPLETED
    );
  }

  getOrgName(organization_id: number): string {
    for (let org of this.organizations) {
      if (org.id === organization_id) {
        return org.name;
      }
    }
    return '<unknown>';
  }

  getCollabName(collab_id: number): string {
    for (let collab of this.collaborations) {
      if (collab.id === collab_id) {
        return collab.name;
      }
    }
    return '<unknown>';
  }

  getAlgorithmStatusMessage(status: string, data: any): string {
    let org_name = this.getOrgName(data.organization_id);
    let collab_name = this.getCollabName(data.collaboration_id);
    if (status === TaskStatus.ACTIVE) {
      return (
        `An algorithm (result_id ${data.result_id}) was just started on ` +
        `a node of organization ${org_name} in collaboration ${collab_name}`
      );
    } else if (status === TaskStatus.COMPLETED) {
      return (
        `An algorithm (result_id ${data.result_id}) just finished for collaboration` +
        ` ${collab_name} (organization ${org_name})`
      );
    } else if (
      status !== TaskStatus.PENDING &&
      status !== TaskStatus.INITIALIZING
    ) {
      return (
        `An algorithm (result_id ${data.result_id}) just failed for collaboration` +
        ` ${collab_name} (organization ${org_name}) with status: ${status}`
      );
    }
    return '';
  }

  private onAlgorithmStatusChange(data: any) {
    if (dictEmpty(data)) return; // ignore initialization values;
    let sentiment = this.isPositiveStatus(data.status)
      ? Sentiment.POSITIVE
      : Sentiment.NEGATIVE;
    let message = this.getAlgorithmStatusMessage(data.status, data);
    if (message) {
      this.snackbarService.openTaskMessageSnackBar(
        message,
        sentiment,
        data.task_id,
        this.userPermission.user.organization_id
      );
    }
  }

  private onCreatedTask(data: any) {
    if (dictEmpty(data)) return; // ignore initialization values;
    let org_name = this.getOrgName(data.init_org_id);
    let collab_name = this.getCollabName(data.collaboration_id);
    this.snackbarService.openTaskMessageSnackBar(
      `A new task (id=${data.task_id}) has just been created in ` +
        `collaboration ${collab_name} by organization ${org_name}`,
      Sentiment.NEUTRAL,
      data.task_id,
      this.userPermission.user.organization_id
    );
  }
}
