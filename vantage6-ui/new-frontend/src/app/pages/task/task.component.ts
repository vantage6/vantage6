import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormArray, FormBuilder, FormControl, Validators } from '@angular/forms';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { Algorithm, Function } from 'src/app/models/api/algorithm.model';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { Collaboration } from 'src/app/models/api/Collaboration.model';
import { Subject, takeUntil } from 'rxjs';

@Component({
  selector: 'app-task',
  templateUrl: './task.component.html',
  styleUrls: ['./task.component.scss']
})
export class TaskComponent implements OnInit, OnDestroy {
  destroy$ = new Subject();
  algorithms: Algorithm[] = [];
  algorithm: Algorithm | null = null;
  function: Function | null = null;

  packageForm = this.fb.nonNullable.group({
    algorithmID: ['', Validators.required],
    name: ['', Validators.required],
    description: ['']
  });

  functionForm = this.fb.nonNullable.group({
    functionName: ['', Validators.required],
    organizationIDs: ['', Validators.required]
  });

  parametersForm = this.fb.nonNullable.group({});

  constructor(
    private fb: FormBuilder,
    private algorithmService: AlgorithmService,
    public chosenCollaborationService: ChosenCollaborationService
  ) {}

  async ngOnInit(): Promise<void> {
    this.algorithms = await this.algorithmService.getAlgorithms();

    this.packageForm.controls.algorithmID.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (algorithmID) => {
      this.algorithm = await this.algorithmService.getAlgorithm(algorithmID);
    });

    this.functionForm.controls.functionName.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (functionName) => {
      this.functionForm.controls.organizationIDs.reset();
      Object.keys(this.parametersForm.controls).forEach((control) => {
        this.parametersForm.removeControl(control);
      });

      this.function = this.algorithm?.functions.find((_) => _.name === functionName) || null;

      this.function?.arguments.forEach((argument) => {
        this.parametersForm.addControl(argument.name, new FormControl('', Validators.required));
      });
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }
}
