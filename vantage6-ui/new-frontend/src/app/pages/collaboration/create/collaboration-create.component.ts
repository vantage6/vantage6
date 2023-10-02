import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { CollaborationCreate, CollaborationForm } from 'src/app/models/api/collaboration.model';
import { routePaths } from 'src/app/routes';
import { CollaborationService } from 'src/app/services/collaboration.service';
import { NodeService } from 'src/app/services/node.service';

@Component({
  selector: 'app-collaboration-create',
  templateUrl: './collaboration-create.component.html',
  styleUrls: ['./collaboration-create.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class CollaborationCreateComponent {
  routes = routePaths;

  isSubmitting = false;

  constructor(
    private router: Router,
    private collaborationService: CollaborationService,
    private nodeService: NodeService
  ) {}

  async handleSubmit(collaborationForm: CollaborationForm) {
    this.isSubmitting = true;

    const collaborationCreate: CollaborationCreate = (({ registerNodes, ...data }) => data)(collaborationForm); //
    const collaboration = await this.collaborationService.createCollaboration(collaborationCreate);
    if (collaboration?.id) {
      if (collaborationForm.registerNodes && collaborationForm.organization_ids) {
        await Promise.all(
          collaborationForm.organization_ids.map(async (organizationID: number) => {
            await this.nodeService.createNode(collaboration, organizationID);
          })
        );
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
