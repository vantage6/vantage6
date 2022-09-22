import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PasswordLostComponent } from './password-lost.component';

describe('PasswordLostComponent', () => {
  let component: PasswordLostComponent;
  let fixture: ComponentFixture<PasswordLostComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [PasswordLostComponent],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(PasswordLostComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
