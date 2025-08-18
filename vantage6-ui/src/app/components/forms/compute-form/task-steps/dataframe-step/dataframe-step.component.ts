import { Component, Input, OnInit, OnDestroy } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { BehaviorSubject, Subject, takeUntil } from 'rxjs';
import { Dataframe } from '../../../../../models/api/session.models';
import { AlgorithmFunctionExtended, FunctionDatabase } from '../../../../../models/api/algorithm.model';
import { BaseSession } from '../../../../../models/api/session.models';
import { TranslateModule } from '@ngx-translate/core';
import { ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { NgIf, NgFor } from '@angular/common';
import { AlertWithButtonComponent } from '../../../../alerts/alert-with-button/alert-with-button.component';
import { routePaths } from '../../../../../routes';
import { ChangesInCreateTaskService } from 'src/app/services/changes-in-create-task.service';
import { SessionService } from 'src/app/services/session.service';
import { BaseOrganization } from 'src/app/models/api/organization.model';
import { TaskDBOutput } from 'src/app/models/api/task.models';
import { compareIDsForSelection } from '../task-create-helper';

@Component({
  selector: 'app-dataframe-step',
  templateUrl: './dataframe-step.component.html',
  styleUrls: ['./dataframe-step.component.scss'],
  imports: [TranslateModule, ReactiveFormsModule, MatFormFieldModule, MatSelectModule, NgIf, NgFor, AlertWithButtonComponent],
  standalone: true
})
export class DataframeStepComponent implements OnInit, OnDestroy {
  compareIDsForSelection = compareIDsForSelection;

  @Input() formGroup!: FormGroup;
  @Input() dataframes: Dataframe[] = [];

  function: AlgorithmFunctionExtended | null = null;
  hasLoadedDataframes: boolean = false;
  selectedDataframes: Dataframe[] = [];
  organizationNamesWithNonReadyDataframes: string[] = [];
  organizations: BaseOrganization[] = [];
  session: BaseSession | null = null;
  selectedOrganizationIDs: string[] = [];

  readonly routes = routePaths;

  private destroy$ = new Subject<void>();
  public readonly initialized$ = new BehaviorSubject<boolean>(false);

  constructor(
    private changesInCreateTaskService: ChangesInCreateTaskService,
    private sessionService: SessionService
  ) {}

  ngOnInit(): void {
    this.setupFormListeners();
    this.setupChangeListeners();
    this.initialized$.next(true);
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  public setupRepeatTask(taskDataframes: TaskDBOutput[]): void {
    if (taskDataframes && taskDataframes.length > 0) {
      taskDataframes.forEach((db, idx) => {
        this.formGroup.controls[`dataframeId${idx}`].setValue(db.dataframe_id?.toString() || '');
        this.handleDataframeChange(`dataframeId${idx}`);
      });
    }
  }

  private setupForm() {
    if (!this.function) return;
    this.function?.databases.forEach((database, index) => {
      const controlName = `dataframeId${index}`;
      this.formGroup.addControl(controlName, new FormControl(null, [Validators.required]));
      // track changes in the dataframe form controls
      this.formGroup
        .get(controlName)
        ?.valueChanges.pipe(takeUntil(this.destroy$))
        .subscribe((dataframeId: number) => {
          this.handleDataframeChange(controlName);
        });
    });
  }

  private setupFormListeners(): void {
    // Listen to changes in all dataframe form controls
    if (this.function?.databases) {
      this.function.databases.forEach((database: FunctionDatabase, index: number) => {
        const controlName = `dataframeId${index}`;
        if (this.formGroup.controls[controlName]) {
          this.formGroup.controls[controlName].valueChanges.pipe(takeUntil(this.destroy$)).subscribe((dataframeId: number) => {
            this.handleDataframeChange(controlName);
          });
        }
      });
    }
  }

  private setupChangeListeners(): void {
    this.changesInCreateTaskService.sessionChange$.pipe(takeUntil(this.destroy$)).subscribe((session) => {
      this.handleSessionChange(session);
    });
    this.changesInCreateTaskService.functionChange$.pipe(takeUntil(this.destroy$)).subscribe((function_) => {
      this.handleFunctionChange(function_);
    });
    this.changesInCreateTaskService.selectedOrganizationIDsChange$.pipe(takeUntil(this.destroy$)).subscribe((organizationIDs) => {
      this.selectedOrganizationIDs = Array.isArray(organizationIDs)
        ? organizationIDs
        : organizationIDs
          ? [organizationIDs as unknown as string]
          : [];
    });
    this.changesInCreateTaskService.organizationChange$.pipe(takeUntil(this.destroy$)).subscribe((organizations) => {
      this.organizations = organizations;
    });
  }

  private async handleSessionChange(session: BaseSession | null): Promise<void> {
    if (!session) return;
    this.session = session;
    this.hasLoadedDataframes = false;
    this.dataframes = await this.sessionService.getDataframes(session.id);
    // filter dataframes that are not ready - they cannot be used for analyses
    this.dataframes = this.dataframes.filter((df) => df.ready);
    this.hasLoadedDataframes = true;
  }

  private handleFunctionChange(function_: AlgorithmFunctionExtended | null): void {
    if (!function_) return;
    this.function = function_;
    // clear the selected dataframes since the function may require a different number
    // of dataframes, and set the new controls
    this.formGroup.reset();
    this.setupForm();
    this.selectedDataframes = [];
    this.changesInCreateTaskService.emitDataframeChange(this.selectedDataframes);
  }

  private handleDataframeChange(controlName: string): void {
    // get all selected dataframes
    let selectedDfs: number[] | number = this.formGroup.get(controlName)?.value;
    if (!selectedDfs) return;
    // if this is a number, convert it to an array
    if (typeof selectedDfs === 'number') {
      selectedDfs = [selectedDfs];
    }
    this.selectedDataframes = this.dataframes.filter((df) => selectedDfs.includes(df.id));
    this.changesInCreateTaskService.emitDataframeChange(this.selectedDataframes);
  }

  get hasDataframes(): boolean {
    return this.dataframes.length > 0;
  }

  get hasFunctionDatabases(): boolean {
    return this.function?.databases != null && this.function.databases.length > 0;
  }

  get shouldShowDataframeSelection(): boolean {
    return this.hasDataframes && this.hasFunctionDatabases;
  }

  get shouldShowNoDataframesAlert(): boolean {
    return this.dataframes.length === 0;
  }

  dataFrameNotReadyForAllSelectedOrganizations(): boolean {
    if (!this.selectedDataframes || this.selectedDataframes.length === 0) return false;
    if (!this.selectedOrganizationIDs || this.selectedOrganizationIDs.length === 0) return false;
    const selectedOrganizationsNotReady = this.selectedOrganizationIDs.filter(
      (org: string) => !this.selectedDataframes.find((df) => df.organizations_ready.includes(Number(org)))
    );
    this.organizationNamesWithNonReadyDataframes = selectedOrganizationsNotReady.map(
      (org: string) => this.organizations.find((o: any) => o.id === Number(org))?.name || ''
    );
    return selectedOrganizationsNotReady.length > 0;
  }
}
