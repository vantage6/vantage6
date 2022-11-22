import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ModalKillComponent } from './modal-kill.component';

describe('ModalKillComponent', () => {
  let component: ModalKillComponent;
  let fixture: ComponentFixture<ModalKillComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ModalKillComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ModalKillComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
