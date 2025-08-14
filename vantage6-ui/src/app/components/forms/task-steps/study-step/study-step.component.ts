import { Component, Input, Output, EventEmitter, OnInit, OnDestroy } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { BaseStudy, StudyOrCollab } from '../../../../models/api/study.model';
import { Collaboration } from '../../../../models/api/collaboration.model';
import { TranslateModule } from '@ngx-translate/core';
import { ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { NgIf, NgFor } from '@angular/common';

@Component({
  selector: 'app-study-step',
  templateUrl: './study-step.component.html',
  styleUrls: ['./study-step.component.scss'],
  imports: [TranslateModule, ReactiveFormsModule, MatFormFieldModule, MatSelectModule, MatButtonModule, NgIf, NgFor],
  standalone: true
})
export class StudyStepComponent implements OnInit, OnDestroy {
  @Input() formGroup!: FormGroup;
  @Input() collaboration: Collaboration | null = null;
  @Input() isStudyCompleted = false;

  @Output() studySelected = new EventEmitter<BaseStudy | null>();

  readonly studyOrCollab = StudyOrCollab;

  private destroy$ = new Subject<void>();

  constructor() {}

  ngOnInit(): void {
    this.setupFormListeners();
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

  onStudySelected(studyID: string): void {
    if (!studyID) {
      this.studySelected.emit(null);
      return;
    }

    if (studyID.startsWith(StudyOrCollab.Study)) {
      const studyId = Number(studyID.substring(StudyOrCollab.Study.length));
      const study = this.collaboration?.studies.find((s) => s.id === studyId) || null;
      this.studySelected.emit(study);
    } else {
      // Collaboration selected (not a specific study)
      this.studySelected.emit(null);
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
