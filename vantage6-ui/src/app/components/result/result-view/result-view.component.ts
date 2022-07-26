import { Component, Input, OnInit } from '@angular/core';
import { Result, getEmptyResult } from 'src/app/interfaces/result';
import { ResultApiService } from 'src/app/services/api/result-api.service';
import { FileService } from 'src/app/services/common/file.service';
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
    protected resultApiService: ResultApiService,
    protected resultDataService: ResultDataService,
    protected modalService: ModalService,
    private fileService: FileService
  ) {
    super(resultApiService, resultDataService, modalService);
  }

  ngOnInit(): void {}

  downloadLog(): void {
    if (this.result.log) {
      const filename = `logs_result_${this.result.id}.txt`;
      this.fileService.downloadTxtFile(this.result.log, filename);
    } else {
      this.modalService.openMessageModal(ModalMessageComponent, [
        'Sorry, there log is empty!',
      ]);
    }
  }
}
