import { Component, HostBinding } from '@angular/core';
import { Router } from '@angular/router';
import { AlgorithmForm } from 'src/app/models/api/algorithm.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';

@Component({
  selector: 'app-algorithm-create',
  templateUrl: './algorithm-create.component.html',
  styleUrl: './algorithm-create.component.scss'
})
export class AlgorithmCreateComponent {
  @HostBinding('class') class = 'card-container';
  routes = routePaths;
  isSubmitting = false;

  constructor(
    private router: Router,
    private algorithmService: AlgorithmService
  ) {}

  async handleSubmit(algorithmForm: AlgorithmForm) {
    this.isSubmitting = true;
    const newAlgorithm = await this.algorithmService.createAlgorithm(algorithmForm);
    if (newAlgorithm?.id) {
      this.router.navigate([routePaths.algorithmManage, newAlgorithm.id]);
    } else {
      this.isSubmitting = false;
    }
  }

  handleCancel(): void {
    this.router.navigate([routePaths.collaborations]);
  }
}
