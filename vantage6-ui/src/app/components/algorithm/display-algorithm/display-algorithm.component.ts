import { Component, HostBinding, Input } from '@angular/core';
import { Subject } from 'rxjs';
import { printDate } from 'src/app/helpers/general.helper';
import { Algorithm, AlgorithmFunction } from 'src/app/models/api/algorithm.model';
import { Visualization } from 'src/app/models/api/visualization.model';
import { routePaths } from 'src/app/routes';
import { FileService } from 'src/app/services/file.service';

@Component({
  selector: 'app-display-algorithm',
  templateUrl: './display-algorithm.component.html',
  styleUrl: './display-algorithm.component.scss'
})
export class DisplayAlgorithmComponent {
  @HostBinding('class') class = 'card-container';
  @Input() algorithm: Algorithm | undefined;
  destroy$ = new Subject<void>();
  printDate = printDate;

  constructor(private fileService: FileService) {}

  routes = routePaths;

  selectedFunction?: AlgorithmFunction;

  selectFunction(functionId: number): void {
    this.selectedFunction = this.algorithm?.functions.find((func: AlgorithmFunction) => func.id === functionId);
  }

  getVisualizationSchemaAsText(vis: Visualization): string {
    return JSON.stringify(vis.schema);
  }

  downloadAlgorithmJson(): void {
    if (!this.algorithm) return;
    const filename = `${this.algorithm.name}.json`;

    // remove all nested ID fields as they should not be included in the download
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const cleanedAlgorithmRepresentation: any = { ...this.algorithm };
    delete cleanedAlgorithmRepresentation.id;
    for (const func of cleanedAlgorithmRepresentation.functions) {
      delete func.id;
      for (const param of func.arguments) {
        delete param.id;
      }
      for (const db of func.databases) {
        delete db.id;
      }
      for (const ui_vis of func.ui_visualizations) {
        delete ui_vis.id;
      }
    }

    // also remove other algorithm store properties that should not be included in the
    // download
    delete cleanedAlgorithmRepresentation.digest;
    delete cleanedAlgorithmRepresentation.status;
    delete cleanedAlgorithmRepresentation.submitted_at;
    delete cleanedAlgorithmRepresentation.approved_at;
    delete cleanedAlgorithmRepresentation.invalidated_at;

    const text = JSON.stringify(cleanedAlgorithmRepresentation, null, 2);
    this.fileService.downloadTxtFile(text, filename);
  }
}
