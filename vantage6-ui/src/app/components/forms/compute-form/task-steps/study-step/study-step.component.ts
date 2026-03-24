import { Component, Input, OnInit, OnDestroy } from '@angular/core';
import { FormGroup, Validators } from '@angular/forms';
import { BehaviorSubject, Subject, takeUntil } from 'rxjs';
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
  @Input() shouldShowStudyStep = false;

  readonly studyOrCollab = StudyOrCollab;

  private destroy$ = new Subject<void>();
  public readonly initialized$ = new BehaviorSubject<boolean>(false);

  constructor(
    private changesInCreateTaskService: ChangesInCreateTaskService,
    private organizationService: OrganizationService
  ) {}

  ngOnInit(): void {
    this.setupFormListeners();
    this.setupChangeListeners();
    this.initData();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  async initData(): Promise<void> {
    // set default for study step: full collaboration (this is not visible but required
    // if there are no studies defined to have a valid form)
    this.formGroup.controls['studyOrCollabID'].setValue(StudyOrCollab.Collaboration + this.collaboration?.id.toString());

    this.updateFormValidation();
    this.initialized$.next(true);
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

  public setupRepeatTask(studyOrCollabId: string): void {
    this.formGroup.controls['studyOrCollabID'].setValue(studyOrCollabId);
  }

  onSessionChange(session: BaseSession | null): void {
    if (!session) return;
    this.formGroup.controls['studyOrCollabID'].reset();
    if (session.study) {
      this.formGroup.controls['studyOrCollabID'].disable();
      this.formGroup.controls['studyOrCollabID'].setValue(StudyOrCollab.Study + session.study.id.toString());
      this.onStudySelected(StudyOrCollab.Study + session.study.id.toString());
    } else {
      this.formGroup.controls['studyOrCollabID'].enable();
    }
    this.updateFormValidation();
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

  private updateFormValidation(): void {
    const studyOrCollabControl = this.formGroup.get('studyOrCollabID');
    if (this.shouldShowStudyStep) {
      studyOrCollabControl?.setValidators(Validators.required);
    } else {
      studyOrCollabControl?.clearValidators();
    }
    studyOrCollabControl?.updateValueAndValidity();
  }
}
