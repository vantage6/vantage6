import { Component, Input, Output, EventEmitter, OnInit, OnDestroy } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { BaseStudy, StudyOrCollab } from '../../../../../models/api/study.model';
import { Collaboration } from '../../../../../models/api/collaboration.model';
import { TranslateModule } from '@ngx-translate/core';
import { ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { NgFor } from '@angular/common';
import { ChangesInCreateTaskService } from '../../../../../services/changes-in-create-task.service';
import { BaseSession } from 'src/app/models/api/session.models';
import { OrganizationService } from 'src/app/services/organization.service';

@Component({
  selector: 'app-study-step',
  templateUrl: './study-step.component.html',
  styleUrls: ['./study-step.component.scss'],
  imports: [TranslateModule, ReactiveFormsModule, MatFormFieldModule, MatSelectModule, MatButtonModule, NgFor],
  standalone: true
})
export class StudyStepComponent implements OnInit, OnDestroy {
  @Input() formGroup!: FormGroup;
  @Input() collaboration: Collaboration | null = null;
  @Input() isStudyCompleted = false;

  readonly studyOrCollab = StudyOrCollab;

  private destroy$ = new Subject<void>();

  constructor(
    private changesInCreateTaskService: ChangesInCreateTaskService,
    private organizationService: OrganizationService
  ) {}

  ngOnInit(): void {
    this.setupFormListeners();
    this.setupChangeListeners();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private setupFormListeners(): void {
    this.formGroup.controls['studyOrCollabID'].valueChanges.pipe(takeUntil(this.destroy$)).subscribe((studyID: string) => {
      this.onStudySelected(studyID);
    });
  }

  private setupChangeListeners(): void {
    this.changesInCreateTaskService.sessionChange$.pipe(takeUntil(this.destroy$)).subscribe((session) => {
      this.onSessionChange(session);
    });
  }

  onSessionChange(session: BaseSession | null): void {
    if (!session) return;
    this.formGroup.controls['studyOrCollabID'].reset();
    this.isStudyCompleted = false;
    if (session.study) {
      this.formGroup.controls['studyOrCollabID'].disable();
      this.formGroup.controls['studyOrCollabID'].setValue(StudyOrCollab.Study + session.study.id.toString());
      this.onStudySelected(StudyOrCollab.Study + session.study.id.toString());
    } else {
      this.formGroup.controls['studyOrCollabID'].enable();
    }
  }

  async onStudySelected(studyID: string): Promise<void> {
    if (!studyID) {
      this.changesInCreateTaskService.emitStudyChange(null);
      return;
    }

    if (studyID.startsWith(StudyOrCollab.Study)) {
      const studyId = Number(studyID.substring(StudyOrCollab.Study.length));
      this.changesInCreateTaskService.emitStudyChange(studyId);

      // also update the organizations available for the task
      const organizations = await this.organizationService.getOrganizations({ study_id: studyId });
      this.changesInCreateTaskService.emitOrganizationChange(organizations);
    } else {
      // Collaboration selected (not a specific study)
      this.changesInCreateTaskService.emitStudyChange(null);
    }
  }

  compareStudyOrCollabForSelection(option: string, value: string): boolean {
    return option === value;
  }

  get studies(): BaseStudy[] {
    return this.collaboration?.studies || [];
  }

  get hasStudies(): boolean {
    return this.studies.length > 0;
  }
}
