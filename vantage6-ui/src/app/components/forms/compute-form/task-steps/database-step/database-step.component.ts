import { Component, Input, OnInit, OnDestroy } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { BaseNode, Database } from '../../../../../models/api/node.model';
import { TranslateModule } from '@ngx-translate/core';
import { ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { NgIf, NgFor } from '@angular/common';
import { AlertComponent } from 'src/app/components/alerts/alert/alert.component';
import { ChangesInCreateTaskService } from 'src/app/services/changes-in-create-task.service';

@Component({
  selector: 'app-database-step',
  templateUrl: './database-step.component.html',
  styleUrls: ['./database-step.component.scss'],
  imports: [TranslateModule, ReactiveFormsModule, MatFormFieldModule, MatSelectModule, NgIf, NgFor, AlertComponent],
  standalone: true
})
export class DatabaseStepComponent implements OnInit, OnDestroy {
  @Input() formGroup!: FormGroup;
  @Input() node: BaseNode | null = null;

  private destroy$ = new Subject<void>();

  availableDatabases: Database[] = [];

  constructor(private changesInCreateTaskService: ChangesInCreateTaskService) {}

  ngOnInit(): void {
    this.setupFormListeners();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private setupFormListeners(): void {
    this.changesInCreateTaskService.nodeDatabasesChange$.pipe(takeUntil(this.destroy$)).subscribe((databases) => {
      this.availableDatabases = databases;
    });
  }

  get hasDatabases(): boolean {
    return this.availableDatabases.length > 0;
  }

  nodeConfigContainsDatabases(): boolean {
    return this.node?.config.find((_) => _.key === 'database_labels') !== undefined;
  }
}
