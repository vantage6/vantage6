import { Component, Input, OnInit } from '@angular/core';
import { Result, getEmptyResult } from 'src/app/interfaces/result';
import { ApiResultService } from 'src/app/services/api/api-result.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { ResultDataService } from 'src/app/services/data/result-data.service';
import { BaseViewComponent } from '../../base/base-view/base-view.component';

@Component({
  selector: 'app-result-view',
  templateUrl: './result-view.component.html',
  styleUrls: ['./result-view.component.scss'],
})
export class ResultViewComponent extends BaseViewComponent implements OnInit {
  @Input() result: Result = getEmptyResult();

  constructor(
    protected apiResultService: ApiResultService,
    protected resultDataService: ResultDataService,
    protected modalService: ModalService
  ) {
    super(apiResultService, resultDataService, modalService);
  }

  ngOnInit(): void {}
}
