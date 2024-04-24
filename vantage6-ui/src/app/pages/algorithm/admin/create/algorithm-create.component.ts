import { Component, HostBinding } from '@angular/core';
import { Router } from '@angular/router';
import { AlgorithmForm } from 'src/app/models/api/algorithm.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';

@Component({
  selector: 'app-algorithm-create',
  templateUrl: './algorithm-create.component.html',
  styleUrl: './algorithm-create.component.scss'
})
export class AlgorithmCreateComponent {
  @HostBinding('class') class = 'card-container';
  routes = routePaths;
  isSubmitting = false;

  constructor(
    private router: Router,
    private algorithmService: AlgorithmService
  ) {}

  async handleSubmit(algorithmForm: AlgorithmForm) {
    this.isSubmitting = true;

    // // eslint-disable-next-line @typescript-eslint/no-unused-vars
    // const collaborationCreate: CollaborationCreate = {
    //   name: collaborationForm.name,
    //   encrypted: collaborationForm.encrypted,
    //   organization_ids: collaborationForm.organizations.map((organization: BaseOrganization) => organization.id)
    // };
    // const collaboration = await this.collaborationService.createCollaboration(collaborationCreate);
    // if (collaboration?.id) {
    //   if (collaborationForm.registerNodes && collaborationForm.organizations) {
    //     this.nodeService.registerNodes(collaboration, collaborationForm.organizations);
    //   }
    //   this.router.navigate([routePaths.collaborations]);
    // } else {
    //   this.isSubmitting = false;
    // }
  }

  handleCancel(): void {
    this.router.navigate([routePaths.collaborations]);
  }
}
