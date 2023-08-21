import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { CreateTask } from '../models/api/task.models';

@Injectable({
  providedIn: 'root'
})
export class TaskService {
  constructor(private apiService: ApiService) {}

  create(createTask: CreateTask) {
    return this.apiService.postForApi('/task', createTask);
  }
}
