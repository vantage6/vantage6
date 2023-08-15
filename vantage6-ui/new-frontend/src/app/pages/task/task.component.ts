import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, FormControl, Validators } from '@angular/forms';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { Algorithm, ArgumentType, Function } from 'src/app/models/api/algorithm.model';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { Subject, takeUntil } from 'rxjs';
import { BaseNode, DatabaseType } from 'src/app/models/api/node.model';
import { getDatabasesFromNode } from 'src/app/helpers/node.helper';

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
  databases: any[] = [];
  node: BaseNode | null = null;

  packageForm = this.fb.nonNullable.group({
    algorithmID: ['', Validators.required],
    name: ['', Validators.required],
    description: ['']
  });

  functionForm = this.fb.nonNullable.group({
    functionName: ['', Validators.required],
    organizationIDs: ['', Validators.required]
  });

  databaseForm = this.fb.nonNullable.group({});

  parameterForm = this.fb.nonNullable.group({});

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
      Object.keys(this.databaseForm.controls).forEach((control) => {
        this.parameterForm.removeControl(control);
      });
      Object.keys(this.parameterForm.controls).forEach((control) => {
        this.parameterForm.removeControl(control);
      });

      const selectedFunction = this.algorithm?.functions.find((_) => _.name === functionName) || null;

      selectedFunction?.arguments.forEach((argument) => {
        if (argument.type === ArgumentType.String) {
          this.parameterForm.addControl(argument.name, new FormControl(null, Validators.required));
        }
        if (argument.type === ArgumentType.Integer) {
          this.parameterForm.addControl(argument.name, new FormControl(null, [Validators.required, Validators.pattern('^[0-9]*$')]));
        }
        if (argument.type === ArgumentType.Float) {
          this.parameterForm.addControl(
            argument.name,
            new FormControl(null, [Validators.required, Validators.pattern('^[0-9]*[,.]?[0-9]*$')])
          );
        }
      });

      selectedFunction?.databases.forEach((database) => {
        this.databaseForm.addControl(`${database.name}_name`, new FormControl(null, [Validators.required]));
        this.databaseForm
          .get(`${database.name}_name`)
          ?.valueChanges.pipe(takeUntil(this.destroy$))
          .subscribe(async (dataBaseName) => {
            this.databaseForm.removeControl(`${database.name}_query`);
            this.databaseForm.removeControl(`${database.name}_sheet`);
            const type = this.databases.find((_) => _.name === dataBaseName)?.type;
            if (type === DatabaseType.SQL || type === DatabaseType.OMOP || type === DatabaseType.Sparql) {
              this.databaseForm.addControl(`${database.name}_query`, new FormControl(null, [Validators.required]));
            }
            if (type === DatabaseType.Excel) {
              this.databaseForm.addControl(`${database.name}_sheet`, new FormControl(null, [Validators.required]));
            }
          });
      });

      this.function = selectedFunction;
    });

    this.functionForm.controls.organizationIDs.valueChanges.pipe(takeUntil(this.destroy$)).subscribe(async (organizationID) => {
      let id = organizationID;
      if (Array.isArray(organizationID) && organizationID.length > 0) {
        id = organizationID[0];
      }

      if (id) {
        const nodes = await this.chosenCollaborationService.getNodes();
        this.node = nodes.find((_) => _.organization.id === Number.parseInt(id)) || null;

        if (this.node) {
          this.databases = getDatabasesFromNode(this.node);
        }
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }
}
