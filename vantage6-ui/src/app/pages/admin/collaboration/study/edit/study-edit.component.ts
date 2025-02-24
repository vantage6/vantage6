import { Component, HostBinding, Input, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { BaseOrganization } from 'src/app/models/api/organization.model';
import { Study, StudyCreate, StudyForm, StudyLazyProperties } from 'src/app/models/api/study.model';
import { routePaths } from 'src/app/routes';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { StudyService } from 'src/app/services/study.service';
import { NgIf } from '@angular/common';
import { PageHeaderComponent } from '../../../../../components/page-header/page-header.component';
import { MatCard, MatCardContent } from '@angular/material/card';
import { StudyFormComponent } from '../../../../../components/forms/study-form/study-form.component';
import { MatProgressSpinner } from '@angular/material/progress-spinner';

@Component({
    selector: 'app-study-edit',
    templateUrl: './study-edit.component.html',
    styleUrls: ['./study-edit.component.scss'],
    imports: [NgIf, PageHeaderComponent, MatCard, MatCardContent, StudyFormComponent, MatProgressSpinner]
})
export class StudyEditComponent implements OnInit {
  @HostBinding('class') class = 'card-container';
  @Input() id: string = '';

  isLoading: boolean = true;
  isSubmitting: boolean = false;
  study?: Study;

  constructor(
    private router: Router,
    private studyService: StudyService,
    private chosenCollaborationService: ChosenCollaborationService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.initData();
    this.isLoading = false;
  }

  private async initData(): Promise<void> {
    this.study = await this.studyService.getStudy(this.id, [StudyLazyProperties.Organizations, StudyLazyProperties.Collaboration]);
  }

  async handleSubmit(studyForm: StudyForm) {
    if (!this.study || !this.study.collaboration) return;

    this.isSubmitting = true;

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const studyCreate: StudyCreate = {
      name: studyForm.name,
      organization_ids: studyForm.organizations.map((organization: BaseOrganization) => organization.id),
      collaboration_id: this.study.collaboration.id
    };
    const result = await this.studyService.editStudy(this.study.id.toString(), studyCreate);

    if (result?.id) {
      // update the chosen collaboration to include the edited study
      this.chosenCollaborationService.refresh(this.study.collaboration.id.toString());
      this.router.navigate([routePaths.study, this.study.id]);
    } else {
      this.isSubmitting = false;
    }
  }

  handleCancel() {
    this.router.navigate([routePaths.collaboration, this.id]);
  }
}
