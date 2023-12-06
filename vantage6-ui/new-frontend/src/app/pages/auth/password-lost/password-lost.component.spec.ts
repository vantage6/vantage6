import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PasswordLostComponent } from './password-lost.component';

describe('PasswordLostComponent', () => {
  let component: PasswordLostComponent;
  let fixture: ComponentFixture<PasswordLostComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [PasswordLostComponent]
    });
    fixture = TestBed.createComponent(PasswordLostComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
