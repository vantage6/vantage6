import {Component, Input, OnInit} from '@angular/core';
import {
  DisplayAlgorithmComponent
} from "../../../../components/algorithm/display-algorithm/display-algorithm.component";
import {AlgorithmLazyProperties} from "../../../../models/api/algorithm.model";
import {AlgorithmService} from "../../../../services/algorithm.service";
import {NgIf} from "@angular/common";
import {MatProgressSpinner} from "@angular/material/progress-spinner";
import {Algorithm} from "src/app/models/api/algorithm.model";

@Component({
  selector: 'app-read-public',
  templateUrl: './algorithm-read-public.component.html',
  imports: [
    DisplayAlgorithmComponent,
    NgIf,
    MatProgressSpinner
  ],
  styleUrl: './algorithm-read-public.component.scss'
})
export class AlgorithmReadPublicComponent implements OnInit {
  @Input() id: string = '';
  algorithm?: Algorithm;
  isLoading = true;

  constructor(
    private algorithmService: AlgorithmService,
  ) {
  }

  async ngOnInit(): Promise<void> {
    this.algorithm = await this.algorithmService.getAlgorithmForCommunityStore(this.id);
    this.isLoading = false;
  }

}
