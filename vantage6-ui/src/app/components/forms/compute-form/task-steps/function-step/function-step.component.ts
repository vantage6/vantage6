import { Component, Input, Output, EventEmitter, OnInit, OnDestroy } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { BehaviorSubject, Subject, takeUntil } from 'rxjs';
import { AlgorithmFunction, AlgorithmFunctionExtended, Argument, Algorithm } from '../../../../../models/api/algorithm.model';
import { BaseOrganization } from '../../../../../models/api/organization.model';
import { AlgorithmStepType, BaseSession } from '../../../../../models/api/session.models';
import { TranslateModule } from '@ngx-translate/core';
import { ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { NgIf, NgFor } from '@angular/common';
import { AlertComponent } from '../../../../alerts/alert/alert.component';
import { HighlightedTextPipe } from '../../../../../pipes/highlighted-text.pipe';
import { Collaboration } from 'src/app/models/api/collaboration.model';
import { ChangesInCreateTaskService } from '../../../../../services/changes-in-create-task.service';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { Task } from 'src/app/models/api/task.models';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { compareIDsForSelection } from '../task-create-helper';

@Component({
  selector: 'app-function-step',
  templateUrl: './function-step.component.html',
  styleUrls: ['./function-step.component.scss'],
  imports: [
    TranslateModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatSelectModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    NgIf,
    NgFor,
    AlertComponent,
    HighlightedTextPipe,
    MatProgressSpinner
  ],
  standalone: true
})
export class FunctionStepComponent implements OnInit, OnDestroy {
  compareIDsForSelection = compareIDsForSelection;

  @Input() formGroup!: FormGroup;
  @Input() node: any = null;
  @Input() algorithms: Algorithm[] = [];
  @Input() collaboration: Collaboration | null | undefined = null;
  @Input() functions: AlgorithmFunctionExtended[] = [];
  @Input() allowedTaskTypes: AlgorithmStepType[] | undefined = [];
  @Input() isLoadingRepeatTask: boolean = false;

  @Output() searchRequested = new EventEmitter<void>();
  @Output() searchCleared = new EventEmitter<void>();

  sessionRestrictedToSameImage: boolean = false;
  showWarningUniqueDFName: boolean = false;
  isLoading: boolean = false;
  selectedFunction: AlgorithmFunctionExtended | null = null;
  organizations: BaseOrganization[] = [];
  functionsFilteredBySearch: AlgorithmFunctionExtended[] = [];
  functionsAllowedForSession: AlgorithmFunctionExtended[] = [];

  readonly algorithmStepType = AlgorithmStepType;

  private destroy$ = new Subject<void>();
  public readonly initialized$ = new BehaviorSubject<boolean>(false);

  constructor(
    private changesInCreateTaskService: ChangesInCreateTaskService,
    private chosenCollaborationService: ChosenCollaborationService
  ) {}

  ngOnInit(): void {
    this.setupFormListeners();
    this.setupChangeListeners();
    this.initData();
    this.initialized$.next(true);
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private setupFormListeners(): void {
    this.formGroup.controls['algorithmFunctionSpec'].valueChanges
      .pipe(takeUntil(this.destroy$))
      .subscribe((algorithmFunctionSpec: string) => {
        this.handleFunctionChange(algorithmFunctionSpec);
      });
    this.formGroup.controls['organizationIDs'].valueChanges
      .pipe(takeUntil(this.destroy$))
      .subscribe((organizationIDs: string[] | string) => {
        const ids = Array.isArray(organizationIDs) ? organizationIDs : organizationIDs ? [organizationIDs] : [];
        this.changesInCreateTaskService.emitSelectedOrganizationIDsChange(ids);
      });
  }

  public async setupRepeatTask(repeatedTask: Task): Promise<void> {
    this.isLoading = true;
    if (!(this.allowedTaskTypes?.length === 1 && this.allowedTaskTypes[0] === AlgorithmStepType.DataExtraction)) {
      // don't set task name for data extraction tasks - it will be used as the name
      // of the created dataframe and that must be unique for the session
      this.formGroup.controls['taskName'].setValue(repeatedTask.name);
    } else {
      this.showWarningUniqueDFName = true;
    }

    this.formGroup.controls['description'].setValue(repeatedTask.description);

    // set function and algorithm
    const algorithm = this.getAlgorithmFromImage(repeatedTask.image);
    if (algorithm === null || algorithm?.algorithm_store_id === undefined) {
      this.isLoading = false;
      return;
    }
    const func =
      this.functionsAllowedForSession.find(
        (_) => _.name === repeatedTask?.method && _.algorithm_id == algorithm?.id && _.algorithm_store_id == algorithm?.algorithm_store_id
      ) || null;
    if (!func) {
      this.isLoading = false;
      return;
    }
    const functionSpec = this.getAlgorithmFunctionSpec(func);
    this.formGroup.controls['algorithmFunctionSpec'].setValue(functionSpec);
    await this.handleFunctionChange(functionSpec, algorithm);

    // select same organizations
    const organizationIDs = repeatedTask.runs.map((_) => _.organization?.id?.toString() ?? '').filter((value) => value);
    this.formGroup.controls['organizationIDs'].setValue(organizationIDs);

    this.isLoading = false;
  }

  private initData(): void {
    this.functionsFilteredBySearch = this.functions;
    this.functionsAllowedForSession = this.functions;
    this.isLoading = false;
  }

  private setupChangeListeners(): void {
    this.changesInCreateTaskService.studyChange$.pipe(takeUntil(this.destroy$)).subscribe((studyId) => {
      this.handleStudyChange();
    });
    this.changesInCreateTaskService.sessionChange$.pipe(takeUntil(this.destroy$)).subscribe((session) => {
      this.handleSessionChange(session);
    });
    this.changesInCreateTaskService.organizationChange$.pipe(takeUntil(this.destroy$)).subscribe((organizations) => {
      this.organizations = organizations;
    });
  }

  private async handleFunctionChange(algorithmFunctionSpec: string, algorithm: Algorithm | undefined = undefined): Promise<void> {
    const [functionName, algorithmID, algorithmStoreID] = algorithmFunctionSpec.split('__');
    // emit the function change
    this.selectedFunction =
      this.functions.find(
        (_) => _.name === functionName && _.algorithm_id == Number(algorithmID) && _.algorithm_store_id == Number(algorithmStoreID)
      ) || null;
    if (!this.selectedFunction) return;
    this.changesInCreateTaskService.emitFunctionChange(this.selectedFunction);
    if (!algorithm) {
      algorithm = this.algorithms.find((_) => _.id === Number(algorithmID) && _.algorithm_store_id == Number(algorithmStoreID));
    }
    if (algorithm) {
      this.changesInCreateTaskService.emitfunctionAlgorithmChange(algorithm);
    }

    // clear the selected organizations - if e.g. first a federated function is selected,
    // then a central compute function, the organizations are not valid anymore
    await this.clearOrganizations();

    // If it's a federated step, select all organizations
    if (this.isFederatedStep(this.selectedFunction.step_type)) {
      this.formGroup.patchValue({
        organizationIDs: this.organizations.map((org) => org.id.toString())
      });
    }
  }

  private handleStudyChange(): void {
    // when study changes, clear the selected organizations as not all of them might be
    // part of the study
    this.clearOrganizations();
  }

  private handleSessionChange(session: BaseSession | null): void {
    if (!session) return;
    this.clearOrganizations();
    // check if session is restricted to same image, if so, filter functions to only
    // include functions that are allowed for the session
    if (this.chosenCollaborationService.collaboration$.value?.session_restrict_to_same_image && session?.image) {
      this.sessionRestrictedToSameImage = true;
      const allowedAlgorithm: Algorithm | null = this.getAlgorithmFromImage(session.image);
      if (allowedAlgorithm) {
        this.functionsAllowedForSession = this.functionsAllowedForSession.filter((func) => func.algorithm_id === allowedAlgorithm.id);
        this.functionsFilteredBySearch = this.functionsAllowedForSession;
      }
    }
    // if function is not in the allowed functions, clear the function
    if (!this.functionsAllowedForSession.some((func) => func.name === this.selectedFunction?.name)) {
      this.selectedFunction = null;
    }
  }

  private async clearOrganizations(): Promise<void> {
    this.formGroup.controls['organizationIDs'].reset();
  }

  onSearch(): void {
    this.searchRequested.emit();
  }

  onClearSearch(): void {
    this.searchCleared.emit();
  }

  isFederatedStep(stepType: AlgorithmStepType): boolean {
    return stepType !== AlgorithmStepType.CentralCompute;
  }

  isDataExtractionStep(): boolean {
    return this.selectedFunction?.step_type === AlgorithmStepType.DataExtraction;
  }

  getFunctionOptionLabel(func: AlgorithmFunctionExtended): string {
    const curAlgorithm = this.algorithms.find((_) => _.id === func.algorithm_id && _.algorithm_store_id == func.algorithm_store_id);
    const storeName = curAlgorithm ? this.getAlgorithmStoreName(curAlgorithm) : '';
    return `${this.getDisplayName(func)} <div class="detail-txt"> | ${func.algorithm_name}, ${storeName}, ${func.step_type}</div>`;
  }

  getDisplayName(obj: AlgorithmFunction | Argument): string {
    return obj.display_name && obj.display_name != '' ? obj.display_name : obj.name;
  }

  getAlgorithmFunctionSpec(func: AlgorithmFunctionExtended): string {
    return `${func.name}__${func.algorithm_id}__${func.algorithm_store_id}`;
  }

  getAlgorithmStoreName(algorithm: Algorithm): string {
    if (this.collaboration?.algorithm_stores && this.collaboration.algorithm_stores.length > 1) {
      const store_name = this.collaboration.algorithm_stores.find((_) => _.url === algorithm.algorithm_store_url)?.name;
      if (store_name) {
        return store_name;
      }
    }
    return '';
  }

  search() {
    const value = this.formGroup.controls['algorithmFunctionSearch'].value;
    this.functionsFilteredBySearch = this.functionsAllowedForSession.filter((func) => {
      const curAlgorithm = this.algorithms.find((_) => _.id === func.algorithm_id && _.algorithm_store_id == func.algorithm_store_id);
      const storeName = curAlgorithm ? this.getAlgorithmStoreName(curAlgorithm) : '';
      return [func.algorithm_name, func.step_type, storeName, func.display_name, func.name].some((val) =>
        val?.toLowerCase()?.includes(value.toLowerCase())
      );
    });
  }

  clearFunctionSearchInput() {
    this.formGroup.controls['algorithmFunctionSearch'].setValue('');
    this.search();
  }

  private getAlgorithmFromImage(image: string): Algorithm | null {
    if (image.includes('@sha256:')) {
      return this.algorithms.find((_) => `${_.image}@${_.digest}` === image) || null;
    } else {
      return this.algorithms.find((_) => _.image === image) || null;
    }
  }
}
