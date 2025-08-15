import { Component, Input, Output, EventEmitter, OnInit, OnDestroy } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { Dataframe } from '../../../../../models/api/session.models';
import { FunctionDatabase } from '../../../../../models/api/algorithm.model';
import { BaseSession } from '../../../../../models/api/session.models';
import { TranslateModule } from '@ngx-translate/core';
import { ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { NgIf, NgFor } from '@angular/common';
import { AlertWithButtonComponent } from '../../../../alerts/alert-with-button/alert-with-button.component';
import { routePaths } from '../../../../../routes';
import { ChangesInCreateTaskService } from 'src/app/services/changes-in-create-task.service';

@Component({
  selector: 'app-dataframe-step',
  templateUrl: './dataframe-step.component.html',
  styleUrls: ['./dataframe-step.component.scss'],
  imports: [TranslateModule, ReactiveFormsModule, MatFormFieldModule, MatSelectModule, NgIf, NgFor, AlertWithButtonComponent],
  standalone: true
})
export class DataframeStepComponent implements OnInit, OnDestroy {
  @Input() formGroup!: FormGroup;
  @Input() dataframes: Dataframe[] = [];
  @Input() function: any = null;
  @Input() session: BaseSession | null = null;
  @Input() organizationNamesWithNonReadyDataframes: string[] = [];
  @Input() selectedDataframes: Dataframe[] = [];
  @Input() organizations: any[] = [];
  @Input() functionForm: FormGroup | null = null;

  readonly routes = routePaths;

  private destroy$ = new Subject<void>();

  constructor(private changesInCreateTaskService: ChangesInCreateTaskService) {}

  ngOnInit(): void {
    this.setupFormListeners();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private setupFormListeners(): void {
    // Listen to changes in all dataframe form controls
    if (this.function?.databases) {
      this.function.databases.forEach((database: FunctionDatabase, index: number) => {
        const controlName = `dataframeId${index}`;
        if (this.formGroup.controls[controlName]) {
          this.formGroup.controls[controlName].valueChanges.pipe(takeUntil(this.destroy$)).subscribe((dataframeId: number) => {
            this.changesInCreateTaskService.emitDataframeChange([dataframeId.toString()]);
          });
        }
      });
    }
  }

  compareIDsForSelection(option: number, value: number): boolean {
    return option === value;
  }

  get hasDataframes(): boolean {
    return this.dataframes.length > 0;
  }

  get hasFunctionDatabases(): boolean {
    return this.function?.databases && this.function.databases.length > 0;
  }

  get shouldShowDataframeSelection(): boolean {
    return this.hasDataframes && this.hasFunctionDatabases;
  }

  get shouldShowNoDataframesAlert(): boolean {
    return this.dataframes.length === 0;
  }

  dataFrameNotReadyForAllSelectedOrganizations(): boolean {
    if (!this.selectedDataframes || this.selectedDataframes.length === 0) return false;
    if (!this.functionForm) return false;

    let selectedOrganizations = this.functionForm.controls['organizationIDs'].value;
    if (!selectedOrganizations) return false;
    if (!Array.isArray(selectedOrganizations)) {
      selectedOrganizations = [selectedOrganizations];
    }
    const selectedOrganizationsNotReady = selectedOrganizations.filter(
      (org: string) => !this.selectedDataframes.find((df) => df.organizations_ready.includes(Number(org)))
    );
    this.organizationNamesWithNonReadyDataframes = selectedOrganizationsNotReady.map(
      (org: string) => this.organizations.find((o: any) => o.id === Number(org))?.name || ''
    );
    return selectedOrganizationsNotReady.length > 0;
  }
}
