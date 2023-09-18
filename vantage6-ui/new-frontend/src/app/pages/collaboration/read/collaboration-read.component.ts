import { Component, Input, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { TranslateService } from '@ngx-translate/core';
import { ConfirmDialog } from 'src/app/components/dialogs/confirm/confirm-dialog.component';
import { Collaboration, CollaborationLazyProperties } from 'src/app/models/api/Collaboration.model';
import { NodeStatus } from 'src/app/models/api/node.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { CollaborationService } from 'src/app/services/collaboration.service';

@Component({
  selector: 'app-collaboration-read',
  templateUrl: './collaboration-read.component.html',
  styleUrls: ['./collaboration-read.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class CollaborationReadComponent implements OnInit {
  nodeStatus = NodeStatus;
  routes = routePaths;

  @Input() id = '';

  isLoading = true;
  collaboration?: Collaboration;
  canDelete = false;
  canEdit = false;

  constructor(
    private dialog: MatDialog,
    private authService: AuthService,
    private collaborationService: CollaborationService,
    private translateService: TranslateService
  ) {}

  async ngOnInit(): Promise<void> {
    this.canDelete = this.authService.isOperationAllowed(ScopeType.ANY, ResourceType.COLLABORATION, OperationType.DELETE);
    this.canEdit = this.authService.isOperationAllowed(ScopeType.ANY, ResourceType.COLLABORATION, OperationType.EDIT);
    this.initData();
  }

  handleNodeClick(id: number): void {
    //TODO: Add navigation to node page
    console.log(id);
  }

  private async initData(): Promise<void> {
    this.collaboration = await this.collaborationService.getCollaboration(this.id, [
      CollaborationLazyProperties.Organizations,
      CollaborationLazyProperties.Nodes
    ]);
    this.isLoading = false;
  }

  handleEdit(): void {
    //TODO: Add navigation to edit page
  }

  async handleDelete(): Promise<void> {
    if (!this.collaboration) return;

    const dialogRef = this.dialog.open(ConfirmDialog, {
      data: {
        title: this.translateService.instant('collaboration-read.delete-dialog.title', { name: this.collaboration.name }),
        content: this.translateService.instant('collaboration-read.delete-dialog.content'),
        confirmButtonText: this.translateService.instant('general.delete'),
        confirmButtonType: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(async (result) => {
      if (result === true) {
        if (!this.collaboration) return;
        await this.collaborationService.delete(this.collaboration.id);
        // this.router.navigate([routePaths.tasks]);
      }
    });
  }
}
