import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BaseUserListComponent } from './base-user-list.component';

describe('BaseUserListComponent', () => {
  let component: BaseUserListComponent;
  let fixture: ComponentFixture<BaseUserListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [BaseUserListComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(BaseUserListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
