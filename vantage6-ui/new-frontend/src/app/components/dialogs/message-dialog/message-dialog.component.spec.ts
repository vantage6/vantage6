import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MessageDialog } from './message-dialog.component';

describe('MessageDialog', () => {
  let component: MessageDialog;
  let fixture: ComponentFixture<MessageDialog>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [MessageDialog]
    });
    fixture = TestBed.createComponent(MessageDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
