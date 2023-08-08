import { Component, OnInit } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { Algorithm } from 'src/app/models/api/algorithm.model';

@Component({
  selector: 'app-task',
  templateUrl: './task.component.html',
  styleUrls: ['./task.component.scss']
})
export class TaskComponent implements OnInit {
  algorithms: Algorithm[] = [];
  form = this.fb.nonNullable.group({
    algorithmID: ['', Validators.required],
    name: ['', Validators.required],
    description: ['']
  });

  constructor(
    private fb: FormBuilder,
    private algorithmService: AlgorithmService
  ) {}

  async ngOnInit(): Promise<void> {
    this.algorithms = await this.algorithmService.getAlgorithms();
  }
}
