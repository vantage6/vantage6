import { Component, HostBinding, Input, OnInit } from '@angular/core';
import { ResourceForm } from 'src/app/models/api/resource.model';

@Component({
  selector: 'app-base-edit',
  templateUrl: './base-edit.component.html',
  styleUrl: './base-edit.component.scss'
})
export abstract class BaseEditComponent implements OnInit {
  @HostBinding('class') class = 'card-container';
  @Input() id: string = '';

  isLoading: boolean = true;
  isSubmitting: boolean = false;

  async ngOnInit(): Promise<void> {
    await this.initData();
  }

  protected abstract initData(): Promise<void>;

  protected abstract handleSubmit(form: ResourceForm): Promise<void>;

  protected abstract handleCancel(): void;
}
