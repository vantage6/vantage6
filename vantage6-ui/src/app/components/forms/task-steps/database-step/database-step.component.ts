import { Component, Input, Output, EventEmitter, OnInit, OnDestroy } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { Database } from '../../../../models/api/node.model';
import { TranslateModule } from '@ngx-translate/core';
import { ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { NgIf, NgFor } from '@angular/common';
import { AlertComponent } from 'src/app/components/alerts/alert/alert.component';

@Component({
  selector: 'app-database-step',
  templateUrl: './database-step.component.html',
  styleUrls: ['./database-step.component.scss'],
  imports: [TranslateModule, ReactiveFormsModule, MatFormFieldModule, MatSelectModule, NgIf, NgFor, AlertComponent],
  standalone: true
})
export class DatabaseStepComponent implements OnInit, OnDestroy {
  @Input() formGroup!: FormGroup;
  @Input() availableDatabases: Database[] = [];

  @Output() databaseSelected = new EventEmitter<string>();

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
    this.formGroup.controls['database'].valueChanges.pipe(takeUntil(this.destroy$)).subscribe((database: string) => {
      this.databaseSelected.emit(database);
    });
  }

  get hasDatabases(): boolean {
    return this.availableDatabases.length > 0;
  }
}
