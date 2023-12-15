import { Component, EventEmitter, Input, OnChanges, OnDestroy, Output, SimpleChanges } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { getDatabasesFromNode } from 'src/app/helpers/node.helper';
import { FunctionDatabase } from 'src/app/models/api/algorithm.model';
import { BaseNode, Database, DatabaseType } from 'src/app/models/api/node.model';
import { TaskDBOutput } from 'src/app/models/api/task.models';

@Component({
  selector: 'app-database-step',
  templateUrl: './database-step.component.html'
})
export class DatabaseStepComponent implements OnDestroy, OnChanges {
  destroy$ = new Subject();

  @Input() form!: FormGroup;
  @Input() functionDatabases: FunctionDatabase[] = [];
  @Input() node!: BaseNode | null;
  @Output() isReady = new EventEmitter<boolean>();

  availableDatabases: Database[] = [];

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['node']?.currentValue) {
      this.getAvailableDatabases();
    }
    if (changes['functionDatabases']?.currentValue || changes['node']?.currentValue) {
      this.setFormControlsForDatabase();
    }
    if (this.node && this.functionDatabases.length > 0) {
      this.isReady.emit(true);
    }
  }

  reset() {
    Object.keys(this.form.controls).forEach((control) => {
      this.form.removeControl(control);
    });
  }

  setDatabasesFromPreviousTask(databases: TaskDBOutput[], functionDatabases: FunctionDatabase[]): void {
    if (databases.length != functionDatabases.length) {
      return; // the algorithm has changed, we cannot use the previous task's databases
    }
    for (let idx = 0; idx < databases.length; idx++) {
      const database = databases[idx];
      const functionDatabase = functionDatabases[idx];
      this.form.get(`${functionDatabase.name}_name`)?.setValue(database.label);
      if (database.parameters) {
        const parameters = JSON.parse(database.parameters);
        Object.keys(parameters).forEach((parameter) => {
          // TODO 'query' and 'sheet_name' should come from some enum
          if (parameter === 'query') {
            this.form.get(`${functionDatabase.name}_query`)?.setValue(parameters[parameter]);
          } else if (parameter === 'sheet_name') {
            this.form.get(`${functionDatabase.name}_sheet`)?.setValue(parameters[parameter]);
          }
        });
      }
    }
  }

  private getAvailableDatabases(): void {
    this.availableDatabases = getDatabasesFromNode(this.node);
  }

  private setFormControlsForDatabase() {
    this.functionDatabases.forEach((database) => {
      this.form.addControl(`${database.name}_name`, new FormControl(null, [Validators.required]));
      this.form
        .get(`${database.name}_name`)
        ?.valueChanges.pipe(takeUntil(this.destroy$))
        .subscribe(async (dataBaseName) => {
          //Clear form
          Object.keys(this.form.controls).forEach((control) => {
            if (control.startsWith(database.name) && !control.includes('_name')) this.form.removeControl(control);
          });

          //Add form controls for selected database
          const type = this.availableDatabases.find((_) => _.name === dataBaseName)?.type;
          if (type === DatabaseType.SQL || type === DatabaseType.OMOP || type === DatabaseType.Sparql) {
            this.form.addControl(`${database.name}_query`, new FormControl(null, [Validators.required]));
          }
          if (type === DatabaseType.Excel) {
            this.form.addControl(`${database.name}_sheet`, new FormControl(null, [Validators.required]));
          }
        });
    });
  }
}
