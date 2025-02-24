import { Component, Input, OnChanges } from '@angular/core';
import { Visualization } from 'src/app/models/api/visualization.model';
import { FileService } from 'src/app/services/file.service';
// import { Chart } from 'chart.js';
import { Chart, LineController, LineElement, PointElement, LinearScale, CategoryScale } from 'chart.js';
import { COLOR_VANTAGE6_PRIMARY } from 'src/app/models/constants/style';
import { isNested } from 'src/app/helpers/utils.helper';
import { MatButton } from '@angular/material/button';
import { TranslateModule } from '@ngx-translate/core';

Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale);

@Component({
    selector: 'app-visualize-line',
    templateUrl: './visualize-line.component.html',
    styleUrl: './visualize-line.component.scss',
    imports: [MatButton, TranslateModule]
})
export class VisualizeLineComponent implements OnChanges {
  @Input() visualization?: Visualization | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  @Input() result: any[] = [];
  @Input() result_id: string = '';

  x: string = '';
  y: string = '';

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data_x: any = [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data_y: any = [];
  name?: string;
  description?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  chart: any;

  constructor(private fileService: FileService) {}

  ngOnChanges(): void {
    // Find the line to visualize in the complete result. E.g. if the result is { data: [1, 2, 3] },
    // location should be set at ['data'] in the visualization schema to get the array
    let lineData = this.result;
    if (this.visualization?.schema?.location) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      this.visualization.schema.location.forEach((key: any) => {
        lineData = lineData[key];
      });
    }

    // if the result is a single table row, convert it to an array of rows
    if (!Array.isArray(lineData) && isNested(lineData)) {
      this.parseDefaultPandasFormat(lineData);
    } else {
      // TODO implement parseRecordsFormat (if algorithm is excluded with pd.to_json(orient='records'))
      console.error('Data format not recognized');
    }
    this.createChart();
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private parseDefaultPandasFormat(lineData: any): void {
    // if columns are defined, use them. Otherwise use the keys of the first result
    if (this.visualization?.schema?.x && this.visualization?.schema?.y) {
      this.x = this.visualization.schema.x as string;
      this.y = this.visualization.schema.y as string;
    }

    // set the data
    this.data_x = Object.values(lineData[this.x]);
    this.data_y = Object.values(lineData[this.y]);
  }

  private createChart(): void {
    // set table name and description
    this.name = this.visualization?.name;
    this.description = this.visualization?.description;

    this.chart = new Chart('LineChart', {
      type: 'line',
      data: {
        labels: this.data_x,
        datasets: [
          {
            label: this.y,
            data: this.data_y,
            fill: false,
            borderColor: COLOR_VANTAGE6_PRIMARY,
            tension: 0.1
          }
        ]
      },
      options: {
        responsive: true,
        scales: {
          x: {
            title: {
              display: true,
              text: this.x
            },
            type: 'linear'
          },
          y: {
            title: {
              display: true,
              text: this.y
            }
          }
        }
      }
    });
    if (this.visualization?.schema['y_axis_min'] !== undefined) {
      this.chart.options.scales.y.min = this.visualization.schema['y_axis_min'] as number;
    }
    if (this.visualization?.schema['y_axis_max'] !== undefined) {
      this.chart.options.scales.y.max = this.visualization.schema['y_axis_max'] as number;
    }
  }

  exportToCsv(): void {
    // Convert data to CSV format
    let csvData = `${this.x},${this.y}\n`;
    for (let i = 0; i < this.data_x.length; i++) {
      csvData += `${this.data_x[i]},${this.data_y[i]}\n`;
    }

    this.fileService.downloadCsvFile(csvData, `vantage6_results_line_${this.result_id}.csv`);
  }
}
