import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, FormControl, Validators } from '@angular/forms';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { Algorithm, ArgumentType, Function } from 'src/app/models/api/algorithm.model';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { Subject, takeUntil } from 'rxjs';

@Component({
  selector: 'app-task',
  templateUrl: './task.component.html',
  styleUrls: ['./task.component.scss']
})
export class TaskComponent implements OnInit, OnDestroy {
  destroy$ = new Subject();
  argumentType = ArgumentType;

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
        if (argument.type === ArgumentType.String) {
          this.parametersForm.addControl(argument.name, new FormControl(null, Validators.required));
        }
        if (argument.type === ArgumentType.Integer) {
          this.parametersForm.addControl(argument.name, new FormControl(null, [Validators.required, Validators.pattern('^[0-9]*$')]));
        }
        if (argument.type === ArgumentType.Float) {
          this.parametersForm.addControl(
            argument.name,
            new FormControl(null, [Validators.required, Validators.pattern('^[0-9]*[,.]?[0-9]*$')])
          );
        }
      });
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }
}
