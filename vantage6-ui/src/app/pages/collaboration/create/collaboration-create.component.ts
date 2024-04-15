import { Component, HostBinding } from '@angular/core';
import { Router } from '@angular/router';
import { CollaborationCreate, CollaborationForm } from 'src/app/models/api/collaboration.model';
import { BaseOrganization } from 'src/app/models/api/organization.model';
import { routePaths } from 'src/app/routes';
import { CollaborationService } from 'src/app/services/collaboration.service';
import { NodeService } from 'src/app/services/node.service';

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
        this.nodeService.registerNodes(collaboration, collaborationForm.organizations);
      }
      this.router.navigate([routePaths.collaborations]);
    } else {
      this.isSubmitting = false;
    }
  }

  handleCancel(): void {
    this.router.navigate([routePaths.collaborations]);
  }

}
