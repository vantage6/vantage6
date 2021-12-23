import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ModalNewUserComponent } from './modal-new-user.component';

describe('ModalNewUserComponent', () => {
  let component: ModalNewUserComponent;
  let fixture: ComponentFixture<ModalNewUserComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ModalNewUserComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ModalNewUserComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
