import { BehaviorSubject } from 'rxjs';
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
import { TaskDataService } from '../data/task-data.service';
import { take } from 'rxjs/operators';

@Injectable({
  providedIn: 'root',
})
export class SocketioMessageService {
  socket_messages = new BehaviorSubject<string[]>([]);
  organizations: Organization[] = [];
  collaborations: Collaboration[] = [];

  constructor(
    private socketioConnectService: SocketioConnectService,
    private orgDataService: OrgDataService,
    private collabDataService: CollabDataService,
    private snackbarService: SnackbarService,
    private userPermission: UserPermissionService,
    private taskDataService: TaskDataService
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
    this.socketioConnectService.getMessages().subscribe((update) => {
      this.addMessage(update);
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

  getSocketMessages() {
    return this.socket_messages.asObservable();
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
    let msg = `The node '${data.name}' just came online!`;
    this.snackbarService.openNodeStatusSnackBar(msg, data, true);
    this.addMessage(msg);
  }

  private onNodeOffline(data: any) {
    let msg = `The node '${data.name}' just went offline!`;
    this.snackbarService.openNodeStatusSnackBar(msg, data, false);
    this.addMessage(msg);
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
        `An algorithm (run_id ${data.run_id}) was just started on ` +
        `a node of organization ${org_name} in collaboration ${collab_name}`
      );
    } else if (status === TaskStatus.COMPLETED) {
      return (
        `An algorithm (run_id ${data.run_id}) just finished for collaboration` +
        ` ${collab_name} (organization ${org_name})`
      );
    } else if (
      status !== TaskStatus.PENDING &&
      status !== TaskStatus.INITIALIZING
    ) {
      return (
        `An algorithm (run_id ${data.run_id}) just failed for collaboration` +
        ` ${collab_name} (organization ${org_name}) with status: ${status}`
      );
    }
    return '';
  }

  private async onAlgorithmStatusChange(data: any) {
    if (dictEmpty(data)) return; // ignore initialization values;
    let sentiment = this.isPositiveStatus(data.status)
      ? Sentiment.POSITIVE
      : Sentiment.NEGATIVE;
    let message = this.getAlgorithmStatusMessage(data.status, data);
    if (message) {
      (await this.taskDataService.get(data.task_id))
        .pipe(take(1))
        .subscribe((task) => {
          // only send message if task of currently logged-in user 1) has
          // finished and is not a subtask or 2) has crashed
          if (
            task.init_user_id === this.userPermission.user.id &&
            ((!task.parent_id && task.status === TaskStatus.COMPLETED) ||
              !this.isPositiveStatus(task.status))
          ) {
            this.snackbarService.openTaskMessageSnackBar(
              message,
              sentiment,
              data.task_id,
              this.userPermission.user.organization_id
            );
          }
        });
      this.addMessage(message);
    }
  }

  private async onCreatedTask(data: any) {
    if (dictEmpty(data)) return; // ignore initialization values;
    let org_name = this.getOrgName(data.init_org_id);
    let collab_name = this.getCollabName(data.collaboration_id);
    let msg =
      `A new task (id=${data.task_id}) has just been created in ` +
      `collaboration ${collab_name} by organization ${org_name}`;
    this.addMessage(msg);

    // create snackbar if logged-in user has created a task so they can view it
    if (data.task_id) {
      (await this.taskDataService.get(data.task_id))
        .pipe(take(1))
        .subscribe((task) => {
          // only send message if task of currently logged-in user is created
          // and they have not been doing so via the UI (otherwise they would
          // already be on the relevant page)
          if (
            task.init_user_id === this.userPermission.user.id &&
            !task.parent_id &&
            !task.created_via_ui
          ) {
            this.snackbarService.openTaskMessageSnackBar(
              'View the task you just created here!',
              Sentiment.NEUTRAL,
              data.task_id,
              this.userPermission.user.organization_id
            );
          }
        });
    }
  }

  addMessage(message: string): void {
    if (!message) return;
    // add message to front of array so latest messages are shown first
    let messages = [message, ...this.socket_messages.value];
    this.socket_messages.next(messages);
  }
}
