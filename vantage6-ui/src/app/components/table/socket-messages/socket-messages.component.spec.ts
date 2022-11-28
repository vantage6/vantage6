import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SocketMessagesComponent } from './socket-messages.component';

describe('SocketMessagesComponent', () => {
  let component: SocketMessagesComponent;
  let fixture: ComponentFixture<SocketMessagesComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ SocketMessagesComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SocketMessagesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
