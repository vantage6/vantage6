import { ComponentFixture, TestBed } from '@angular/core/testing';

import { UserViewSingleComponent } from './user-view-single.component';

describe('UserViewSingleComponent', () => {
  let component: UserViewSingleComponent;
  let fixture: ComponentFixture<UserViewSingleComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ UserViewSingleComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(UserViewSingleComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
