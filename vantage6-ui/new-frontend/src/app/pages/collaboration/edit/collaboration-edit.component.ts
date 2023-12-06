import { Component, HostBinding, Input, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Collaboration, CollaborationCreate, CollaborationForm, CollaborationLazyProperties } from 'src/app/models/api/collaboration.model';
import { routePaths } from 'src/app/routes';
import { CollaborationService } from 'src/app/services/collaboration.service';
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
    private nodeService: NodeService
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
    const collaborationCreate: CollaborationCreate = (({ registerNodes, ...data }) => data)(collaborationForm);
    const result = await this.collaborationService.editCollaboration(this.collaboration?.id.toString(), collaborationCreate);

    if (result?.id) {
      if (collaborationForm.registerNodes && collaborationForm.organization_ids) {
        // register nodes of new organizations in collaboration
        const newOrganizationIDs = collaborationForm.organization_ids.filter(
          (id: number) => !this.collaboration?.organizations.find((organization) => organization.id === id)
        );
        await Promise.all(
          newOrganizationIDs.map(async (organizationID: number) => {
            if (!this.collaboration) return;
            await this.nodeService.createNode(this.collaboration, organizationID);
          })
        );
        // delete nodes of organizations that are not in collaboration anymore
        const removedOrganizationIDs = this.collaboration.organizations
          .filter((organization) => !collaborationForm.organization_ids?.includes(organization.id))
          .map((organization) => organization.id);
        await Promise.all(
          removedOrganizationIDs.map(async (organizationID: number) => {
            if (!this.collaboration) return;
            await this.nodeService.deleteNode(this.collaboration, organizationID);
          })
        );
      }
      this.router.navigate([routePaths.collaboration, this.id]);
    } else {
      this.isSubmitting = false;
    }
  }

  handleCancel() {
    this.router.navigate([routePaths.collaboration, this.id]);
  }
}
