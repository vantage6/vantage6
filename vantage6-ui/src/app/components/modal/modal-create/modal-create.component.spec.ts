import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ModalCreateComponent } from './modal-create.component';

describe('ModalCreateComponent', () => {
  let component: ModalCreateComponent;
  let fixture: ComponentFixture<ModalCreateComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ModalCreateComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ModalCreateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
