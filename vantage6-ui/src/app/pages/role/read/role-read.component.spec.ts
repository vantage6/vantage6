import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RoleReadComponent } from './role-read.component';

describe('RoleReadComponent', () => {
  let component: RoleReadComponent;
  let fixture: ComponentFixture<RoleReadComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [RoleReadComponent]
    });
    fixture = TestBed.createComponent(RoleReadComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
