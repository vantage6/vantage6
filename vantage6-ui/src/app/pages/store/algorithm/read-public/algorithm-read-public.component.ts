import { Component, Input, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { DisplayAlgorithmComponent } from 'src/app/components/algorithm/display-algorithm/display-algorithm.component';
import { AlgorithmService } from 'src/app/services/algorithm.service';

import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { Algorithm } from 'src/app/models/api/algorithm.model';

@Component({
  selector: 'app-read-public',
  templateUrl: './algorithm-read-public.component.html',
  imports: [DisplayAlgorithmComponent, MatProgressSpinner],
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './algorithm-read-public.component.scss'
})
export class AlgorithmReadPublicComponent implements OnInit {
  @Input() id: string = '';
  algorithm?: Algorithm;
  isLoading = true;

  constructor(private algorithmService: AlgorithmService) {}

  async ngOnInit(): Promise<void> {
    this.algorithm = await this.algorithmService.getAlgorithmForCommunityStore(this.id);
    this.isLoading = false;
  }
}
