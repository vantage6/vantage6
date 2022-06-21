import { Component, Input, OnInit } from '@angular/core';
import { Result, getEmptyResult } from 'src/app/interfaces/result';
import { ApiResultService } from 'src/app/services/api/api-result.service';
import { DownloadFileService } from 'src/app/services/common/download-file.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { ResultDataService } from 'src/app/services/data/result-data.service';
import { BaseViewComponent } from '../../base/base-view/base-view.component';
import { ModalMessageComponent } from '../../modal/modal-message/modal-message.component';

@Component({
  selector: 'app-result-view',
  templateUrl: './result-view.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './result-view.component.scss',
  ],
})
export class ResultViewComponent extends BaseViewComponent implements OnInit {
  @Input() result: Result = getEmptyResult();

  constructor(
    protected apiResultService: ApiResultService,
    protected resultDataService: ResultDataService,
    protected modalService: ModalService,
    private downloadFileService: DownloadFileService
  ) {
    super(apiResultService, resultDataService, modalService);
  }

  ngOnInit(): void {}

  downloadLog(): void {
    if (this.result.log) {
      const filename = `logs_result_${this.result.id}.txt`;
      this.downloadFileService.downloadTxtFile(this.result.log, filename);
    } else {
      this.modalService.openMessageModal(ModalMessageComponent, [
        'Sorry, there log is empty!',
      ]);
    }
  }
}
