import { Component, Input, OnInit } from '@angular/core';
import { Run, getEmptyRun } from 'src/app/interfaces/run';
import { RunApiService } from 'src/app/services/api/run-api.service';
import { FileService } from 'src/app/services/common/file.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { RunDataService } from 'src/app/services/data/run-data.service';
import { BaseViewComponent } from '../base-view/base-view.component';

@Component({
  selector: 'app-run-view',
  templateUrl: './run-view.component.html',
  styleUrls: ['../../../shared/scss/buttons.scss', './run-view.component.scss'],
})
export class RunViewComponent extends BaseViewComponent implements OnInit {
  @Input() run: Run = getEmptyRun();

  constructor(
    protected RunApiService: RunApiService,
    protected RunDataService: RunDataService,
    protected modalService: ModalService,
    private fileService: FileService
  ) {
    super(RunApiService, RunDataService, modalService);
  }

  ngOnInit(): void {}

  downloadLog(): void {
    if (this.run.log) {
      const filename = `vantage6_logs_run_${this.run.id}.txt`;
      this.fileService.downloadTxtFile(this.run.log, filename);
    } else {
      this.modalService.openMessageModal([
        'Sorry, the log is empty, nothing to download!',
      ]);
    }
  }

  getResultDisplay(): string {
    let MAX_DISPLAY_LEN = 2000;
    if (!this.run.decrypted_result) {
      return '';
    } else if (this.run.decrypted_result?.length < MAX_DISPLAY_LEN) {
      return this.run.decrypted_result;
    } else {
      let len_not_shown = this.run.decrypted_result.length - MAX_DISPLAY_LEN;
      return (
        this.run.decrypted_result.slice(0, MAX_DISPLAY_LEN) +
        ` (${len_not_shown} characters shown)...`
      );
    }
  }

  downloadResult(): void {
    /// TODO if collaboration is encrypted, take that into account here
    if (this.run.result) {
      const filename = `vantage6_results_${this.run.id}.txt`;
      if (this.run.decrypted_result) {
        // TODO call result file JSON if we get here?
        this.fileService.downloadTxtFile(this.run.decrypted_result, filename);
      } else {
        this.fileService.downloadTxtFile(this.run.result, filename);
        this.modalService.openMessageModal([
          'We could not decode your results here. Please execute the two steps' +
            ' below to decode them yourself',
          'First, the results are b64 encoded. Decode them.',
          'Finally, the results are serialized at the end of the algorithm' +
            ' you used, so you should deserialize them. Hint: many Python-based ' +
            'algorithms use Pickle serialization. Then, do `pickle.loads(result)`.',
        ]);
      }
    } else {
      this.modalService.openMessageModal([
        'Sorry, the results are empty, nothing to download!',
      ]);
    }
  }
}
