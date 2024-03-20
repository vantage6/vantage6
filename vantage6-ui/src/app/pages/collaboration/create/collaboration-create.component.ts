import { Component, HostBinding } from '@angular/core';
import { Router } from '@angular/router';
import { CollaborationCreate, CollaborationForm } from 'src/app/models/api/collaboration.model';
import { ApiKeyExport } from 'src/app/models/api/node.model';
import { BaseOrganization } from 'src/app/models/api/organization.model';
import { routePaths } from 'src/app/routes';
import { CollaborationService } from 'src/app/services/collaboration.service';
import { NodeService } from 'src/app/services/node.service';
import { FileService } from 'src/app/services/file.service';
import { MatDialog } from '@angular/material/dialog';
import { MessageDialogComponent } from 'src/app/components/dialogs/message-dialog/message-dialog.component';
import { TranslateService } from '@ngx-translate/core';

@Component({
  selector: 'app-collaboration-create',
  templateUrl: './collaboration-create.component.html'
})
export class CollaborationCreateComponent {
  @HostBinding('class') class = 'card-container';
  routes = routePaths;
  isSubmitting = false;

  constructor(
    private router: Router,
    private collaborationService: CollaborationService,
    private nodeService: NodeService,
    private dialog: MatDialog,
    private translateService: TranslateService,
    private fileService: FileService
  ) {}

  async handleSubmit(collaborationForm: CollaborationForm) {
    this.isSubmitting = true;

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const collaborationCreate: CollaborationCreate = {
      name: collaborationForm.name,
      encrypted: collaborationForm.encrypted,
      organization_ids: collaborationForm.organizations.map((organization: BaseOrganization) => organization.id)
    };
    const collaboration = await this.collaborationService.createCollaboration(collaborationCreate);
    if (collaboration?.id) {
      if (collaborationForm.registerNodes && collaborationForm.organizations) {
        const api_keys: ApiKeyExport[] = [];
        await Promise.all(
          collaborationForm.organizations.map(async (organization: BaseOrganization) => {
            const node = await this.nodeService.createNode(collaboration, organization.id);
            if (node?.api_key) {
              api_keys.push({
                organization: organization.name,
                api_key: node.api_key
              });
            }
          })
        );
        this.downloadApiKeys(api_keys, collaboration.name);
        this.alertApiKeyDownload();
      }
      this.router.navigate([routePaths.collaborations]);
    } else {
      this.isSubmitting = false;
    }
  }

  handleCancel(): void {
    this.router.navigate([routePaths.collaborations]);
  }

  private downloadApiKeys(api_keys: ApiKeyExport[], collaboration_name: string): void {
    const filename = `API_keys_${collaboration_name}.txt`;
    const text = api_keys.map((api_key) => `${api_key.organization}: ${api_key.api_key}`).join('\n');
    this.fileService.downloadTxtFile(text, filename);
  }

  alertApiKeyDownload(): void {
    this.dialog.open(MessageDialogComponent, {
      data: {
        title: this.translateService.instant('api-key-download-dialog.title'),
        content: [
          this.translateService.instant('api-key-download-dialog.create-message'),
          this.translateService.instant('api-key-download-dialog.security-message')
        ],
        confirmButtonText: this.translateService.instant('general.close'),
        confirmButtonType: 'default'
      }
    });
  }
}
