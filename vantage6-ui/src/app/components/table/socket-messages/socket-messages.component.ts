import { Component, OnInit, ViewChild } from '@angular/core';
import { merge, of } from 'rxjs';
import { startWith, switchMap } from 'rxjs/operators';

import { SocketioMessageService } from 'src/app/services/common/socketio-message.service';
import { MatPaginator } from '@angular/material/paginator';

@Component({
  selector: 'app-socket-messages',
  templateUrl: './socket-messages.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    '../../table/base-table/table.component.scss',
    './socket-messages.component.scss',
  ],
})
export class SocketMessagesComponent implements OnInit {
  messages: string[] = [];
  displayed_messages: string[] = [];

  dataSource: any[];

  @ViewChild(MatPaginator, { static: true }) paginator: MatPaginator;

  constructor(private socketMessageService: SocketioMessageService) {}

  ngOnInit(): void {
    this.setMessages();

    // set up pagination
    this.paginator.pageSize = 10;
    this.setPagination();
  }

  protected async setMessages() {
    this.socketMessageService.getSocketMessages().subscribe((messages) => {
      this.messages = messages;
      this.setPagination();
    });
  }

  setPagination() {
    this.paginator.length = this.messages.length;
    this.linkListToPaginator();
  }

  linkListToPaginator() {
    merge(this.paginator.page)
      .pipe(
        startWith({}),
        switchMap(() => {
          return of(this.messages);
        })
      )
      .subscribe((res) => {
        const from = this.paginator.pageIndex * this.paginator.pageSize;
        const to = from + this.paginator.pageSize;
        this.displayed_messages = res.slice(from, to);
      });
  }
}
