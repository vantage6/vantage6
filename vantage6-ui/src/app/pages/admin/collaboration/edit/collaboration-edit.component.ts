import { Component, HostBinding, Input, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { MessageDialogComponent } from 'src/app/components/dialogs/message-dialog/message-dialog.component';
import { Collaboration, CollaborationCreate, CollaborationForm, CollaborationLazyProperties } from 'src/app/models/api/collaboration.model';
import { ApiKeyExport } from 'src/app/models/api/node.model';
import { BaseOrganization } from 'src/app/models/api/organization.model';
import { routePaths } from 'src/app/routes';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { CollaborationService } from 'src/app/services/collaboration.service';
import { FileService } from 'src/app/services/file.service';
import { NodeService } from 'src/app/services/node.service';

@Component({
  selector: 'app-collaboration-edit',
  templateUrl: './collaboration-edit.component.html'
})
export class CollaborationEditComponent implements OnInit {
  @HostBinding('class') class = 'card-container';
  @Input() id: string = '';

  isLoading: boolean = true;
  isSubmitting: boolean = false;
  collaboration?: Collaboration;

  constructor(
    private router: Router,
    private collaborationService: CollaborationService,
    private nodeService: NodeService,
    private dialog: MatDialog,
    private translateService: TranslateService,
    private fileService: FileService,
    private chosenCollaborationService: ChosenCollaborationService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.initData();
    this.isLoading = false;
  }

  private async initData(): Promise<void> {
    this.collaboration = await this.collaborationService.getCollaboration(this.id, [CollaborationLazyProperties.Organizations]);
  }

  async handleSubmit(collaborationForm: CollaborationForm) {
    if (!this.collaboration) return;

    this.isSubmitting = true;

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const collaborationCreate: CollaborationCreate = {
      name: collaborationForm.name,
      encrypted: collaborationForm.encrypted,
      organization_ids: collaborationForm.organizations.map((organization: BaseOrganization) => organization.id)
    };
    const result = await this.collaborationService.editCollaboration(this.collaboration?.id.toString(), collaborationCreate);

    if (result?.id) {
      if (collaborationForm.registerNodes && collaborationForm.organizations) {
        // register nodes of new organizations in collaboration
        const newOrganizations = collaborationForm.organizations.filter(
          (org_in_updated_collab: BaseOrganization) =>
            !this.collaboration?.organizations.find((organization) => organization.id === org_in_updated_collab.id)
        );
        const new_api_keys: ApiKeyExport[] = [];
        await Promise.all(
          newOrganizations.map(async (organization: BaseOrganization) => {
            if (!this.collaboration) return;
            const node = await this.nodeService.createNode(this.collaboration, organization.id);
            if (node?.api_key) {
              new_api_keys.push({
                organization: organization.name,
                api_key: node.api_key
              });
            }
          })
        );
        if (new_api_keys.length > 0) {
          this.downloadApiKeys(new_api_keys, collaborationForm.name);
          this.alertApiKeyDownload();
        }
        // delete nodes of organizations that are not in collaboration anymore
        const removedOrganizationIDs = this.collaboration.organizations
          .filter((organization) => !collaborationForm.organizations?.map((form_org) => form_org.id).includes(organization.id))
          .map((organization) => organization.id);
        await Promise.all(
          removedOrganizationIDs.map(async (organizationID: number) => {
            if (!this.collaboration) return;
            await this.nodeService.deleteNode(this.collaboration, organizationID);
          })
        );
      }
      // update the chosen collaboration
      this.chosenCollaborationService.refresh(result.id.toString());
      // go to the collaboration page
      this.router.navigate([routePaths.collaboration, this.id]);
    } else {
      this.isSubmitting = false;
    }
  }

  handleCancel() {
    this.router.navigate([routePaths.collaboration, this.id]);
  }

  // TODO refactor this component - following is duplicate from collaboration-create.component.ts
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
          this.translateService.instant('api-key-download-dialog.edit-message'),
          this.translateService.instant('api-key-download-dialog.security-message')
        ],
        confirmButtonText: this.translateService.instant('general.close'),
        confirmButtonType: 'default'
      }
    });
  }
}
