import { Component, Input } from '@angular/core';
import { Router } from '@angular/router';
import { BaseOrganization } from 'src/app/models/api/organization.model';
import { StudyCreate, StudyForm } from 'src/app/models/api/study.model';
import { routePaths } from 'src/app/routes';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { StudyService } from 'src/app/services/study.service';

@Component({
  selector: 'app-study-create',
  templateUrl: './study-create.component.html',
  styleUrls: ['./study-create.component.scss']
})
export class StudyCreateComponent {
  routes = routePaths;
  isSubmitting = false;

  @Input() id: string = '';

  constructor(
    private router: Router,
    private studyService: StudyService,
    private chosenCollaborationService: ChosenCollaborationService
  ) {}

  async handleSubmit(studyForm: StudyForm) {
    this.isSubmitting = true;

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const studyCreate: StudyCreate = {
      name: studyForm.name,
      organization_ids: studyForm.organizations.map((organization: BaseOrganization) => organization.id),
      collaboration_id: +this.id
    };
    const study = await this.studyService.createStudy(studyCreate);
    if (study?.id) {
      // update the chosen collaboration to include the new study
      this.chosenCollaborationService.refresh(this.id);
      this.router.navigate([routePaths.study, study.id]);
    } else {
      this.isSubmitting = false;
    }
  }

  handleCancel(): void {
    this.router.navigate([routePaths.collaborations]);
  }
}
